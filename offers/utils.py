"""
offers/utils.py
===============
Single source of offer logic for the entire project.

Priority rule (mandatory):
  ProductOffer > CategoryOffer — never mix.
  CategoryOffer only applies if category.is_offer_applicable = True.

Validity rule:
  is_active = True  AND  valid_from <= now  AND  (valid_until is None OR valid_until >= now)
"""
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# LOW-LEVEL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _is_offer_valid(offer):
    """Return True if the offer passes all validity checks."""
    now = timezone.now()
    return (
        offer.is_active
        and offer.valid_from <= now
        and (offer.valid_until is None or offer.valid_until >= now)
    )


def apply_discount(price, discount_pct):
    """Return discounted price as Decimal, rounded to 2 dp."""
    price        = Decimal(str(price))
    discount_pct = Decimal(str(discount_pct))
    if discount_pct <= 0:
        return price
    discounted = price * (1 - discount_pct / 100)
    return discounted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE PRODUCT — used in Product Detail view
# ─────────────────────────────────────────────────────────────────────────────

def get_applicable_offer(product):
    """
    Returns (discount_pct: Decimal, offer_type: str) for a product.

    discount_pct — 0 if no offer
    offer_type   — 'product' | 'category' | ''

    Uses prefetched/cached relations; safe to call N times without extra queries
    as long as product.category is prefetch_related in the view.
    """
    # ── 1. ProductOffer wins ──────────────────────────────────────────────────
    try:
        po = product.offer   # reverse OneToOne from offers.ProductOffer
        if _is_offer_valid(po):
            return Decimal(str(po.discount_pct)), 'product'
    except Exception:
        pass

    # ── 2. CategoryOffer (any applicable category) ───────────────────────────
    try:
        cats = product.category.all()
    except Exception:
        cats = []

    for cat in cats:
        if not getattr(cat, 'is_offer_applicable', True):
            continue
        try:
            co = cat.offer   # reverse OneToOne from offers.CategoryOffer
            if _is_offer_valid(co):
                return Decimal(str(co.discount_pct)), 'category'
        except Exception:
            continue

    return Decimal('0'), ''


def get_offer_context(product, price):
    """
    Convenience wrapper that returns a dict ready to unpack into a template context.
    Keys:  has_offer, offer_pct, offer_type, effective_price, original_price, savings
    """
    pct, offer_type = get_applicable_offer(product)
    has_offer       = pct > 0
    original        = Decimal(str(price))
    effective       = apply_discount(price, pct) if has_offer else original
    savings         = (original - effective).quantize(Decimal('0.01')) if has_offer else Decimal('0')
    return {
        'has_offer'      : has_offer,
        'offer_pct'      : int(pct) if pct == int(pct) else pct,
        'offer_type'     : offer_type,
        'effective_price': effective,
        'original_price' : original,
        'savings'        : savings,
        
    }


# ─────────────────────────────────────────────────────────────────────────────
# BATCH — annotate a list of ProductVariant objects (no N+1)
# Used in Home, Store, Cart, Checkout views.
# ─────────────────────────────────────────────────────────────────────────────

def annotate_variants_with_offers(variants):
    """
    Takes a list/queryset of ProductVariant objects.
    Attaches to each variant in-memory:
        .has_offer        bool
        .offer_pct        Decimal (0 if none)
        .offer_type       str 'product'|'category'|''
        .offer_label      str e.g. '20% OFF'
        .effective_price  Decimal  (discounted or original)
        .original_price   Decimal  (always original)
        .savings          Decimal

    Performs exactly 2 DB queries for the entire batch (one ProductOffer query,
    one CategoryOffer query) — no per-variant queries.

    The queryset must already have `product__category` prefetched.
    """
    now = timezone.now()

    # Collect product IDs
    product_ids = {v.product_id for v in variants}
    if not product_ids:
        return variants

    # ── Fetch all valid ProductOffers for this batch ──────────────────────────
    from offers.models import ProductOffer
    valid_po = ProductOffer.objects.filter(
        product_id__in=product_ids,
        is_active=True,
        valid_from__lte=now,
    ).filter(
        # valid_until null OR >= now  (Django ORM can't do OR with field=None cleanly;
        # use two querysets merged)
        valid_until__isnull=True
    ) | ProductOffer.objects.filter(
        product_id__in=product_ids,
        is_active=True,
        valid_from__lte=now,
        valid_until__gte=now,
    )
    # product_id → discount_pct
    product_offer_map = {po.product_id: Decimal(str(po.discount_pct)) for po in valid_po}

    # ── Fetch all valid CategoryOffers ────────────────────────────────────────
    from offers.models import CategoryOffer
    valid_co = CategoryOffer.objects.filter(
        is_active=True,
        valid_from__lte=now,
        category__is_offer_applicable=True,
    ).filter(
        valid_until__isnull=True
    ).select_related('category') | CategoryOffer.objects.filter(
        is_active=True,
        valid_from__lte=now,
        valid_until__gte=now,
        category__is_offer_applicable=True,
    ).select_related('category')
    # category_id → discount_pct
    category_offer_map = {co.category_id: Decimal(str(co.discount_pct)) for co in valid_co}

    # ── Annotate each variant ─────────────────────────────────────────────────
    for variant in variants:
        pid = variant.product_id
        pct        = Decimal('0')
        offer_type = ''

        if pid in product_offer_map:
            # ProductOffer wins
            pct        = product_offer_map[pid]
            offer_type = 'product'
        else:
            # Try CategoryOffer
            try:
                cats = variant.product.category.all()
            except Exception:
                cats = []
            for cat in cats:
                if not getattr(cat, 'is_offer_applicable', True):
                    continue
                if cat.id in category_offer_map:
                    pct        = category_offer_map[cat.id]
                    offer_type = 'category'
                    break

        has_offer         = pct > 0
        original          = Decimal(str(variant.price))
        effective         = apply_discount(original, pct) if has_offer else original
        savings           = (original - effective).quantize(Decimal('0.01'))

        variant.has_offer       = has_offer
        variant.offer_pct       = int(pct) if pct == int(pct) else pct
        variant.offer_type      = offer_type
        variant.offer_label     = f'{int(pct)}% OFF' if has_offer else ''
        variant.effective_price = effective
        variant.original_price  = original
        variant.savings         = savings

    return variants