from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Min, Max
from django.core.paginator import Paginator
from store.models import ProductVariant
from category.models import Category
from brands.models import Brand
from wishlist.models import Wishlist
from carts.models import CartItem
from carts.views import _get_or_create_cart


def store(request, category_slug=None):
    keyword        = request.GET.get('q', '').strip()
    category_slugs = request.GET.getlist('category')
    brand_slugs    = request.GET.getlist('brand')
    min_price      = request.GET.get('min_price', '').strip()
    max_price      = request.GET.get('max_price', '').strip()
    sort           = request.GET.get('sort', '')

    # ── Base queryset — active brands AND active categories only ─────
    if category_slug:
        category_obj = get_object_or_404(Category, slug=category_slug, status='active')
        variants = ProductVariant.objects.filter(
            product__category=category_obj,
            product__brand__status='active',
            is_available=True,
            stock__gt=0
        ).select_related('product', 'product__brand')
        if not category_slugs:
            category_slugs = [category_slug]
    else:
        variants = ProductVariant.objects.filter(
            product__brand__status='active',
            product__category__status='active',
            is_available=True,
            stock__gt=0
        ).select_related('product', 'product__brand').distinct()

    cart = _get_or_create_cart(request)

    cart_ids = set(
        CartItem.objects.filter(cart=cart, is_active=True)
        .values_list('variant_id', flat=True)
    )

    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(
            Wishlist.objects.filter(user=request.user)
            .values_list('variant_id', flat=True)
        )
    if category_slugs:
        variants = variants.filter(
            product__category__slug__in=category_slugs,
            product__category__status='active'
        )

    if brand_slugs:
        variants = variants.filter(product__brand__slug__in=brand_slugs)

    if min_price and min_price.isdigit():
        variants = variants.filter(price__gte=int(min_price))
    if max_price and max_price.isdigit():
        variants = variants.filter(price__lte=int(max_price))

    if keyword:
        variants = variants.filter(
            Q(product__product_name__icontains=keyword) |
            Q(product__category__category_name__icontains=keyword) |
            Q(product__brand__brand_name__icontains=keyword) |
            Q(color_name__icontains=keyword)
        ).distinct()

    if sort == 'price_asc':
        variants = variants.order_by('price')
    elif sort == 'price_desc':
        variants = variants.order_by('-price')
    else:
        variants = variants.order_by('id')

    paginator      = Paginator(variants, 15)
    page           = request.GET.get('page')
    paged_variants = paginator.get_page(page)

    # Sidebar — only active categories and brands
    all_categories = Category.objects.filter(status='active')
    all_brands     = Brand.objects.filter(
        status='active',
        product__variants__is_available=True
    ).distinct()

    price_bounds = ProductVariant.objects.filter(
        product__brand__status='active',
        product__category__status='active',
        is_available=True,
        stock__gt=0
    ).aggregate(min=Min('price'), max=Max('price'))

    context = {
        'products': paged_variants,
        'product_count': variants.count(),
        'all_categories': all_categories,
        'all_brands': all_brands,
        'price_min_bound': price_bounds['min'] or 0,
        'price_max_bound': price_bounds['max'] or 100000,
        'active_categories': category_slugs,
        'active_brands': brand_slugs,
        'active_min_price': min_price,
        'active_max_price': max_price,
        'active_sort': sort,
        'keyword': keyword,

        # ✅ ADD THIS
        'cart_ids': cart_ids,
        'wishlist_ids': wishlist_ids,
    }
    return render(request, 'store/store.html', context)

