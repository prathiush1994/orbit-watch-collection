from django.shortcuts import render, redirect
from django.db.models import Avg

from store.models import ProductVariant
from carts.models import CartItem
from carts.views import _get_or_create_cart
from wishlist.models import Wishlist
from offers.utils import get_applicable_offer, apply_discount
from reviews.models import Review
from reviews.forms import ReviewForm
from reviews.views import _user_has_purchased


def product_detail(request, category_slug, variant_slug):
    try:
        variant = ProductVariant.objects.select_related(
            'product', 'product__brand'
        ).prefetch_related(
            'product__category'
        ).get(slug=variant_slug, is_available=True)
    except ProductVariant.DoesNotExist:
        return redirect('store')

    if variant.product.brand and variant.product.brand.status != 'active':
        return redirect('store')

    active_cats = variant.product.category.filter(status='active')
    if not active_cats.exists():
        return redirect('store')

    gallery_images = variant.images.all()
    all_variants   = variant.get_all_variants()

    # ── Offer ─────────────────────────────────────────────────────────────────
    offer_pct, offer_label, offer_type = get_applicable_offer(variant.product)
    effective_price = apply_discount(variant.price, offer_pct)
    has_offer       = offer_pct > 0

    # ── Annotate all_variants with offer info too (for swatch prices) ─────────
    from offers.utils import annotate_variants_with_offers
    all_variants_list = list(all_variants)
    annotate_variants_with_offers(all_variants_list)

    savings = variant.price - effective_price

    # ── Cart ──────────────────────────────────────────────────────────────────
    cart    = _get_or_create_cart(request)
    in_cart = CartItem.objects.filter(
        cart=cart, variant=variant, is_active=True
    ).exists()

    # ── Wishlist ──────────────────────────────────────────────────────────────
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(
            user=request.user, variant=variant
        ).exists()

    # ── Reviews ───────────────────────────────────────────────────────────────
    reviews = Review.objects.filter(variant=variant).select_related('user')

    review_stats = reviews.aggregate(avg=Avg('rating'))
    avg_rating   = round(review_stats['avg'] or 0, 1)
    review_count = reviews.count()

    # Star breakdown (5 → 1)
    star_breakdown = {}
    for star in range(5, 0, -1):
        count = reviews.filter(rating=star).count()
        pct   = int((count / review_count * 100)) if review_count else 0
        star_breakdown[star] = {'count': count, 'pct': pct}

    # Current user state for reviews
    user_review       = None
    can_review        = False
    already_reviewed  = False

    if request.user.is_authenticated:
        user_review      = reviews.filter(user=request.user).first()
        already_reviewed = user_review is not None
        can_review       = (
            not already_reviewed
            and _user_has_purchased(request.user, variant)
        )

    review_form = ReviewForm() if can_review else None

    return render(request, 'store/product_detail.html', {
        'variant'        : variant,
        'product'        : variant.product,
        'gallery_images' : gallery_images,
        'all_variants'   : all_variants_list,
        'in_cart'        : in_cart,
        'in_wishlist'    : in_wishlist,
        # Offer context
        'offer_pct'      : offer_pct,
        'offer_label'    : offer_label,
        'offer_type'     : offer_type,
        'effective_price': effective_price,
        'has_offer'      : has_offer,
        'savings'        : savings,
        # Review context
        'reviews'        : reviews,
        'avg_rating'     : avg_rating,
        'review_count'   : review_count,
        'star_breakdown' : star_breakdown,
        'user_review'    : user_review,
        'can_review'     : can_review,
        'already_reviewed': already_reviewed,
        'review_form'    : review_form,
    })