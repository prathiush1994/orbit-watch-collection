from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from offers.models import ProductOffer
from offers.models import CategoryOffer


def _is_offer_valid(offer):
    now = timezone.now()
    return (
        offer.is_active
        and offer.valid_from <= now
        and (offer.valid_until is None or offer.valid_until >= now)
    )


def apply_discount(price, discount_pct):
    price = Decimal(str(price))
    discount_pct = Decimal(str(discount_pct))
    if discount_pct <= 0:
        return price
    discounted = price * (1 - discount_pct / 100)
    return discounted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_applicable_offer(product):
    product_pct = Decimal("0")
    category_pct = Decimal("0")

    try:
        for po in product.offers.all():
            if _is_offer_valid(po):
                product_pct = max(
                    product_pct,
                    Decimal(str(po.discount_pct))
                )
    except Exception:
        pass

    try:
        cats = product.category.all()
    except Exception:
        cats = []

    for cat in cats:
        if not getattr(cat, "is_offer_applicable", True):
            continue

        try:
            for co in cat.offers.all():
                if _is_offer_valid(co):
                    category_pct = max(
                        category_pct,
                        Decimal(str(co.discount_pct))
                    )
        except Exception:
            pass

    if product_pct >= category_pct:
        return product_pct, "product" if product_pct > 0 else ""

    return category_pct, "category" if category_pct > 0 else ""


def get_offer_context(product, price):
    pct, offer_type = get_applicable_offer(product)
    has_offer = pct > 0
    original = Decimal(str(price))
    effective = apply_discount(price, pct) if has_offer else original
    savings = (
        (original - effective).quantize(Decimal("0.01")) if has_offer else Decimal("0")
    )
    return {
        "has_offer": has_offer,
        "offer_pct": int(pct) if pct == int(pct) else pct,
        "offer_type": offer_type,
        "effective_price": effective,
        "original_price": original,
        "savings": savings,
    }


def annotate_variants_with_offers(variants):
    now = timezone.now()

    product_ids = {v.product_id for v in variants}
    if not product_ids:
        return variants

    valid_po = ProductOffer.objects.filter(
        product_id__in=product_ids,
        is_active=True,
        valid_from__lte=now,
    ).filter(valid_until__isnull=True) | ProductOffer.objects.filter(
        product_id__in=product_ids,
        is_active=True,
        valid_from__lte=now,
        valid_until__gte=now,
    )
    product_offer_map = {
        po.product_id: Decimal(str(po.discount_pct)) for po in valid_po
    }

    valid_co = CategoryOffer.objects.filter(
        is_active=True,
        valid_from__lte=now,
        category__is_offer_applicable=True,
    ).filter(valid_until__isnull=True).select_related(
        "category"
    ) | CategoryOffer.objects.filter(
        is_active=True,
        valid_from__lte=now,
        valid_until__gte=now,
        category__is_offer_applicable=True,
    ).select_related(
        "category"
    )
    category_offer_map = {
        co.category_id: Decimal(str(co.discount_pct)) for co in valid_co
        }
    for variant in variants:
        pid = variant.product_id

        product_pct = product_offer_map.get(pid, Decimal("0"))
        category_pct = Decimal("0")

        try:
            cats = variant.product.category.all()
        except Exception:
            cats = []

        for cat in cats:
            if not getattr(cat, "is_offer_applicable", True):
                continue

            if cat.id in category_offer_map:
                category_pct = max(
                    category_pct,
                    category_offer_map[cat.id]
                )

        if product_pct >= category_pct:
            pct = product_pct
            offer_type = "product" if pct > 0 else ""
        else:
            pct = category_pct
            offer_type = "category"

        has_offer = pct > 0
        original = Decimal(str(variant.price))
        effective = apply_discount(original, pct) if has_offer else original
        savings = (original - effective).quantize(Decimal("0.01"))

        variant.has_offer = has_offer
        variant.offer_pct = int(pct) if pct == int(pct) else pct
        variant.offer_type = offer_type
        variant.offer_label = f"{int(pct)}% OFF" if has_offer else ""
        variant.effective_price = effective
        variant.original_price = original
        variant.savings = savings

    return variants
