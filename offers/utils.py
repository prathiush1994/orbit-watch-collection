"""
from decimal import Decimal


def get_best_offer_price(variant):
    ----------#####
    Returns (effective_price, discount_pct, offer_label) for a variant.
    Applies the LARGEST discount between product offer and category offer.
    If no offer → returns original price, 0, ''.
    ----------#####
    base_price = Decimal(str(variant.price))
    product    = variant.product

    product_pct  = Decimal('0')
    category_pct = Decimal('0')

    # Product-level offer
    try:
        po = product.offer
        if po.is_valid():
            product_pct = po.discount_pct
    except Exception:
        pass

    # Category-level offer
    try:
        co = product.category.offer
        if co.is_valid():
            category_pct = co.discount_pct
    except Exception:
        pass

    best_pct = max(product_pct, category_pct)

    if best_pct <= 0:
        return base_price, Decimal('0'), ''

    discounted = round(base_price - (base_price * best_pct / 100), 2)
    label      = f'{best_pct}% off'
    return discounted, best_pct, label
"""
"""
offers/utils.py
===============
Core offer logic. Import from views and templates.

Rules (from spec):
  1. ProductOffer takes priority over CategoryOffer completely.
  2. CategoryOffer only applies if the category has is_offer_applicable=True.
  3. Offer must be active and within valid date range.
  4. Discounts apply BEFORE coupons and wallet at checkout.
"""
from decimal import Decimal
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE VARIANT  — used in product detail page
# ─────────────────────────────────────────────────────────────────────────────

def get_applicable_offer(product):
    """
    Returns (discount_pct, offer_label, offer_type) for a product.
      - discount_pct : Decimal  (0 if no offer)
      - offer_label  : str      e.g. '15% OFF'  or ''
      - offer_type   : str      'product' | 'category' | ''

    Expects product to have .offer and .category pre-fetched or accessible.
    """
    now = timezone.now()

    # ── 1. Check ProductOffer ─────────────────────────────────────────────────
    try:
        po = product.offer
        if (po.is_active
                and po.valid_from <= now
                and (po.valid_until is None or po.valid_until >= now)):
            pct = Decimal(str(po.discount_pct))
            return pct, f'{pct:g}% OFF', 'product'
    except Exception:
        pass   # no ProductOffer

    # ── 2. Check CategoryOffer (any applicable category) ─────────────────────
    for cat in product.category.all():
        if not cat.is_offer_applicable:
            continue
        try:
            co = cat.offer
            if (co.is_active
                    and co.valid_from <= now
                    and (co.valid_until is None or co.valid_until >= now)):
                pct = Decimal(str(co.discount_pct))
                return pct, f'{pct:g}% OFF', 'category'
        except Exception:
            continue

    return Decimal('0'), '', ''


def apply_discount(price, discount_pct):
    """Returns discounted price given original price and discount %."""
    price        = Decimal(str(price))
    discount_pct = Decimal(str(discount_pct))
    if discount_pct <= 0:
        return price
    return round(price * (1 - discount_pct / 100), 2)


# ─────────────────────────────────────────────────────────────────────────────
# BATCH  — annotate a queryset of variants without N+1 queries
# Use this in store/home views when showing a LIST of products.
# ─────────────────────────────────────────────────────────────────────────────

def annotate_variants_with_offers(variants):
    """
    Takes a list/queryset of ProductVariant objects and attaches offer info
    to each variant in-memory.  No extra per-item DB queries.

    After this call each variant has:
        variant.offer_pct       : Decimal (0 if none)
        variant.offer_label     : str     ('' if none)
        variant.offer_type      : str     'product'|'category'|''
        variant.effective_price : Decimal (discounted or original)
        variant.original_price  : Decimal (always original)

    How to use:
        variants = list(ProductVariant.objects.select_related(...).prefetch_related(...))
        annotate_variants_with_offers(variants)
        # now each variant has the above attributes
    """
    now = timezone.now()

    # Collect all product IDs and category IDs from this batch
    product_ids  = {v.product_id for v in variants}

    # ── Fetch all ProductOffers for this batch in ONE query ───────────────────
    from offers.models import ProductOffer
    product_offers = {
        po.product_id: po
        for po in ProductOffer.objects.filter(
            product_id__in=product_ids,
            is_active=True,
            valid_from__lte=now,
        ).filter(
            # valid_until null OR >= now
            valid_until__isnull=True
        ) | ProductOffer.objects.filter(
            product_id__in=product_ids,
            is_active=True,
            valid_from__lte=now,
            valid_until__gte=now,
        )
    }

    # ── Fetch all CategoryOffers in ONE query ─────────────────────────────────
    # We need the category → offer mapping
    from offers.models import CategoryOffer
    category_offers = {
        co.category_id: co
        for co in CategoryOffer.objects.filter(
            is_active=True,
            valid_from__lte=now,
            category__is_offer_applicable=True,
        ).filter(
            valid_until__isnull=True
        ) | CategoryOffer.objects.filter(
            is_active=True,
            valid_from__lte=now,
            valid_until__gte=now,
            category__is_offer_applicable=True,
        ).select_related('category')
    }

    # ── Annotate each variant ─────────────────────────────────────────────────
    for variant in variants:
        pct        = Decimal('0')
        label      = ''
        offer_type = ''

        # ProductOffer wins
        po = product_offers.get(variant.product_id)
        if po:
            pct        = Decimal(str(po.discount_pct))
            label      = f'{pct:g}% OFF'
            offer_type = 'product'
        else:
            # Try category offers — variant's product can have multiple categories
            # We pre-fetch categories in the view queryset
            try:
                cats = variant.product.category.all()
            except Exception:
                cats = []
            for cat in cats:
                if not cat.is_offer_applicable:
                    continue
                co = category_offers.get(cat.id)
                if co:
                    pct        = Decimal(str(co.discount_pct))
                    label      = f'{pct:g}% OFF'
                    offer_type = 'category'
                    break

        variant.offer_pct       = pct
        variant.offer_label     = label
        variant.offer_type      = offer_type
        variant.original_price  = Decimal(str(variant.price))
        variant.effective_price = apply_discount(variant.price, pct)

    return variants