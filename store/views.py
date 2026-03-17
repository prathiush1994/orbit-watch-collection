from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Q, Min, Max
from store.models import ProductVariant, Product
from category.models import Category
from brands.models import Brand
from carts.models import CartItem
from carts.views import _cart_id
from django.core.paginator import Paginator


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
        'products'          : paged_variants,
        'product_count'     : variants.count(),
        'links'             : Category.objects.all(),   # navbar — show all
        'all_categories'    : all_categories,
        'all_brands'        : all_brands,
        'price_min_bound'   : price_bounds['min'] or 0,
        'price_max_bound'   : price_bounds['max'] or 100000,
        'active_categories' : category_slugs,
        'active_brands'     : brand_slugs,
        'active_min_price'  : min_price,
        'active_max_price'  : max_price,
        'active_sort'       : sort,
        'keyword'           : keyword,
    }
    return render(request, 'store/store.html', context)


def search_suggestions(request):
    q       = request.GET.get('q', '').strip()
    results = []
    if len(q) >= 2:
        products   = Product.objects.filter(
            product_name__icontains=q
        ).values_list('product_name', flat=True).distinct()[:5]

        categories = Category.objects.filter(
            category_name__icontains=q,
            status='active'
        ).values_list('category_name', flat=True).distinct()[:3]

        brands     = Brand.objects.filter(
            brand_name__icontains=q,
            status='active'
        ).values_list('brand_name', flat=True).distinct()[:3]

        results = list(products) + list(categories) + list(brands)
        results = list(dict.fromkeys(results))[:8]

    return JsonResponse({'suggestions': results})


def product_detail(request, category_slug, variant_slug):
    try:
        variant = ProductVariant.objects.select_related(
            'product', 'product__brand'
        ).get(slug=variant_slug, is_available=True)
    except ProductVariant.DoesNotExist:
        return redirect('store')

    # Redirect if brand or category is inactive
    if variant.product.brand and variant.product.brand.status != 'active':
        return redirect('store')

    active_cats = variant.product.category.filter(status='active')
    if not active_cats.exists():
        return redirect('store')

    gallery_images = variant.images.all()
    all_variants   = variant.get_all_variants()

    in_cart = CartItem.objects.filter(
        cart__cart_id=_cart_id(request),
        variant=variant
    ).exists()

    context = {
        'variant'        : variant,
        'product'        : variant.product,
        'gallery_images' : gallery_images,
        'all_variants'   : all_variants,
        'in_cart'        : in_cart,
    }
    return render(request, 'store/product_detail.html', context)