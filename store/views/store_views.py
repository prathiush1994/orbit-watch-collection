from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Min, Max
from django.core.paginator import Paginator
from store.models import ProductVariant
from category.models import Category
from brands.models import Brand
from carts.models import CartItem
from carts.views import _get_or_create_cart
from wishlist.models import WishlistItem
from wishlist.views import _get_or_create_wishlist
from offers.utils import annotate_variants_with_offers


def store(request, category_slug=None):
    keyword = request.GET.get("q", "").strip()
    category_slugs = request.GET.getlist("category")
    brand_slugs = request.GET.getlist("brand")
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    sort = request.GET.get("sort", "")

    # ── Base queryset ─────────────────────────────
    base_qs_kwargs = dict(
        product__brand__status="active",
        is_available=True,
        stock__gt=0,
    )

    if category_slug:
        category_obj = get_object_or_404(Category, slug=category_slug, status="active")
        variants = ProductVariant.objects.filter(
            product__category=category_obj, **base_qs_kwargs
        )
        if not category_slugs:
            category_slugs = [category_slug]
    else:
        variants = ProductVariant.objects.filter(
            product__category__status="active", **base_qs_kwargs
        ).distinct()

    variants = variants.select_related("product", "product__brand").prefetch_related(
        "product__category",
        "product__offer",
        "product__category__offer",
    )
    
    # ── Filters ─────────────────────────────
    if category_slugs:
        variants = variants.filter(
            product__category__slug__in=category_slugs,
            product__category__status="active",
        )

    if brand_slugs:
        variants = variants.filter(product__brand__slug__in=brand_slugs)

    if min_price and min_price.isdigit():
        variants = variants.filter(price__gte=int(min_price))

    if max_price and max_price.isdigit():
        variants = variants.filter(price__lte=int(max_price))

    if keyword:
        variants = variants.filter(
            Q(product__product_name__icontains=keyword)
            | Q(product__category__category_name__icontains=keyword)
            | Q(product__brand__brand_name__icontains=keyword)
            | Q(color_name__icontains=keyword)
        ).distinct()

    # ── Sorting ─────────────────────────────
    if sort == "price_asc":
        variants = variants.order_by("price")
    elif sort == "price_desc":
        variants = variants.order_by("-price")
    else:
        variants = variants.order_by("id")

    # ── Pagination ──────────────────────────
    paginator = Paginator(variants, 15)
    paged_variants = paginator.get_page(request.GET.get("page"))

    # ── Offer annotation ────────────────────
    annotate_variants_with_offers(list(paged_variants.object_list))

    # ── Cart IDs ────────────────────────────
    cart = _get_or_create_cart(request)

    cart_variant_ids = set(
        CartItem.objects.filter(cart=cart, is_active=True).values_list(
            "variant_id", flat=True
        )
    )

    # ── Wishlist IDs (guest + user) ─────────
    wishlist = _get_or_create_wishlist(request)

    wishlist_ids = set(
        WishlistItem.objects.filter(wishlist=wishlist).values_list(
            "variant_id", flat=True
        )
    )

    # ── Sidebar data ────────────────────────
    all_categories = Category.objects.filter(status="active")

    all_brands = Brand.objects.filter(
        status="active", product__variants__is_available=True
    ).distinct()

    price_bounds = ProductVariant.objects.filter(
        product__brand__status="active",
        product__category__status="active",
        is_available=True,
        stock__gt=0,
    ).aggregate(min=Min("price"), max=Max("price"))
    active_categories_set = set(category_slugs)
    active_brands_set = set(brand_slugs)
    return render(
        request,
        "store/store.html",
        {
            "products": paged_variants,
            "product_count": variants.count(),
            "all_categories": all_categories,
            "all_brands": all_brands,
            "price_min_bound": price_bounds["min"] or 0,
            "price_max_bound": price_bounds["max"] or 100000,
            "active_categories": category_slugs,
            "active_brands": brand_slugs,
            "active_min_price": min_price,
            "active_max_price": max_price,
            "active_sort": sort,
            "keyword": keyword,
            "cart_variant_ids": cart_variant_ids,
            "wishlist_ids": wishlist_ids,
            "active_categories_set": active_categories_set,
            "active_brands_set": active_brands_set,
        },
    )
