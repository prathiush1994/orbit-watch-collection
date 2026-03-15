from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Min, Max
from store.models import ProductVariant, Product
from category.models import Category
from brands.models import Brand
from carts.models import CartItem
from carts.views import _cart_id
from django.core.paginator import Paginator


def store(request, category_slug=None):
    """
    Store listing page with full filter system.

    Supported GET parameters:
        q          — keyword search
        category   — comma-separated category slugs  e.g. men,women
        brand      — comma-separated brand slugs     e.g. titan,fossil
        min_price  — minimum price
        max_price  — maximum price
        sort       — price_asc | price_desc
        page       — pagination

    URL examples:
        /store/
        /store/?q=titan
        /store/?category=men&brand=titan&min_price=1000&max_price=10000&sort=price_desc
        /store/?q=titan&brand=titan&sort=price_desc&page=2
    """

    # ── Read all GET parameters ───────────────────────────────────────
    keyword         = request.GET.get('q', '').strip()
    category_slugs  = request.GET.getlist('category')   # multiple checkboxes
    brand_slugs     = request.GET.getlist('brand')       # multiple checkboxes
    min_price       = request.GET.get('min_price', '').strip()
    max_price       = request.GET.get('max_price', '').strip()
    sort            = request.GET.get('sort', '')

    # ── Base queryset ─────────────────────────────────────────────────
    # If a URL category_slug is given (e.g. /store/men/), pre-filter by it
    if category_slug:
        category_obj = get_object_or_404(Category, slug=category_slug)
        variants = ProductVariant.objects.filter(
            product__category=category_obj,
            is_available=True,
            stock__gt=0
        ).select_related('product', 'product__brand')
        # Pre-select the category slug in the sidebar
        if not category_slugs:
            category_slugs = [category_slug]
    else:
        variants = ProductVariant.objects.filter(
            is_available=True,
            stock__gt=0
        ).select_related('product', 'product__brand')

    # ── 1. Category filter ────────────────────────────────────────────
    if category_slugs:
        variants = variants.filter(
            product__category__slug__in=category_slugs
        )

    # ── 2. Brand filter ───────────────────────────────────────────────
    if brand_slugs:
        variants = variants.filter(
            product__brand__slug__in=brand_slugs
        )

    # ── 3. Price range filter ─────────────────────────────────────────
    if min_price and min_price.isdigit():
        variants = variants.filter(price__gte=int(min_price))
    if max_price and max_price.isdigit():
        variants = variants.filter(price__lte=int(max_price))

    # ── 4. Keyword search ─────────────────────────────────────────────
    if keyword:
        variants = variants.filter(
            Q(product__product_name__icontains=keyword) |
            Q(product__category__category_name__icontains=keyword) |
            Q(product__brand__brand_name__icontains=keyword) |
            Q(color_name__icontains=keyword)
        ).distinct()

    # ── 5. Sorting ────────────────────────────────────────────────────
    if sort == 'price_asc':
        variants = variants.order_by('price')
    elif sort == 'price_desc':
        variants = variants.order_by('-price')
    else:
        variants = variants.order_by('id')

    # ── 6. Pagination ─────────────────────────────────────────────────
    paginator      = Paginator(variants, 6)
    page           = request.GET.get('page')
    paged_variants = paginator.get_page(page)

    # ── Sidebar data ──────────────────────────────────────────────────
    all_categories = Category.objects.all()
    all_brands     = Brand.objects.filter(
        product__variants__is_available=True
    ).distinct()

    # Price bounds for the range inputs (from available products)
    price_bounds = ProductVariant.objects.filter(
        is_available=True, stock__gt=0
    ).aggregate(min=Min('price'), max=Max('price'))

    context = {
        # Products
        'products'        : paged_variants,
        'product_count'   : variants.count(),

        # Sidebar data
        'links'           : all_categories,   # navbar category links
        'all_categories'  : all_categories,
        'all_brands'      : all_brands,
        'price_min_bound' : price_bounds['min'] or 0,
        'price_max_bound' : price_bounds['max'] or 100000,

        # Active filter values (to keep checkboxes ticked & inputs filled)
        'active_categories' : category_slugs,
        'active_brands'     : brand_slugs,
        'active_min_price'  : min_price,
        'active_max_price'  : max_price,
        'active_sort'       : sort,
        'keyword'           : keyword,
    }
    return render(request, 'store/store.html', context)


def search_suggestions(request):
    """AJAX endpoint for live search suggestions."""
    q       = request.GET.get('q', '').strip()
    results = []

    if len(q) >= 2:
        products   = Product.objects.filter(
            product_name__icontains=q
        ).values_list('product_name', flat=True).distinct()[:5]

        categories = Category.objects.filter(
            category_name__icontains=q
        ).values_list('category_name', flat=True).distinct()[:3]

        brands     = Brand.objects.filter(
            brand_name__icontains=q
        ).values_list('brand_name', flat=True).distinct()[:3]

        results = list(products) + list(categories) + list(brands)
        results = list(dict.fromkeys(results))[:8]

    return JsonResponse({'suggestions': results})


def product_detail(request, category_slug, variant_slug):
    """Product detail page for one specific variant."""
    variant = get_object_or_404(
        ProductVariant,
        slug=variant_slug,
        is_available=True
    )

    gallery_images = variant.images.all()
    all_variants   = variant.get_all_variants()

    in_cart = CartItem.objects.filter(
        cart__cart_id=_cart_id(request),
        variant=variant
    ).exists()

    context = {
        'variant'       : variant,
        'product'       : variant.product,
        'gallery_images': gallery_images,
        'all_variants'  : all_variants,
        'in_cart'       : in_cart,
    }
    return render(request, 'store/product_detail.html', context)