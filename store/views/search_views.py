from django.http import JsonResponse
from store.models import Product
from category.models import Category
from brands.models import Brand


def search_suggestions(request):
    q= request.GET.get('q', '').strip()
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

