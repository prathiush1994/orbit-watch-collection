from django.shortcuts import render
from store.models import ProductVariant


def home(request):
    # is_available is the correct field name (not is_active)
    men = ProductVariant.objects.filter(
        product__category__slug='men',
        is_available=True
    ).select_related('product').order_by('-price')[:6]

    women = ProductVariant.objects.filter(
        product__category__slug='women',
        is_available=True
    ).select_related('product').order_by('-price')[:6]

    kids = ProductVariant.objects.filter(
        product__category__slug='kids',
        is_available=True
    ).select_related('product').order_by('-price')[:6]

    context = {
        'men_products'  : men,
        'women_products': women,
        'kids_products' : kids,
    }
    return render(request, 'home.html', context)