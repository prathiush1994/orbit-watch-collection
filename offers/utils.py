from decimal import Decimal


def get_best_offer_price(variant):
    """
    Returns (effective_price, discount_pct, offer_label) for a variant.
    Applies the LARGEST discount between product offer and category offer.
    If no offer → returns original price, 0, ''.
    """
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