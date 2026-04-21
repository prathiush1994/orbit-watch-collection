from django.shortcuts import render
from store.models import ProductVariant
from offers.utils import annotate_variants_with_offers


def home(request):
    men = list(ProductVariant.objects.filter(
        product__category__slug='men',
        is_available=True
    ).select_related('product').prefetch_related('product__category').order_by('-created_at')[:11])

    women = list(ProductVariant.objects.filter(
        product__category__slug='women',
        is_available=True
    ).select_related('product').prefetch_related('product__category').order_by('-created_at')[:11])

    kids = list(ProductVariant.objects.filter(
        product__category__slug='kids',
        is_available=True
    ).select_related('product').prefetch_related('product__category').order_by('-created_at')[:11])

    annotate_variants_with_offers(men)
    annotate_variants_with_offers(women)
    annotate_variants_with_offers(kids)

    return render(request, 'home.html', {
        'men_products': men,
        'women_products': women,
        'kids_products': kids,
    })