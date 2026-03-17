from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.utils.text import slugify

from brands.models import Brand
from adminpanel.utils import save_cropped_image

from .decorators import admin_required


def _unique_slug(brand_name, exclude_id=None):
    """Return a unique slug for the given brand name."""
    base = slugify(brand_name)
    slug = base
    qs   = Brand.objects.all()
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    counter = 1
    while qs.filter(slug=slug).exists():
        slug = f'{base}-{counter}'
        counter += 1
    return slug


@admin_required
def brand_list(request):
    search_query = request.GET.get('q', '').strip()

    brands = Brand.objects.all().order_by('-created_at')

    if search_query:
        brands = brands.filter(brand_name__icontains=search_query)

    paginator = Paginator(brands, 15)
    page      = request.GET.get('page', 1)
    brands    = paginator.get_page(page)

    # All names for datalist search hints
    all_brand_names = Brand.objects.values_list("brand_name", flat=True).order_by("brand_name")

    context = {
        'brands'       : brands,
        'search_query'    : search_query,
        'all_brand_names' : all_brand_names,
    }
    return render(request, 'adminpanel/brands.html', context)


@admin_required
def brand_add(request):
    if request.method == 'POST':
        brand_name  = request.POST.get('brand_name', '').strip()
        image_data  = request.POST.get('logo_image', '')   # base64 from crop modal

        if not brand_name:
            messages.error(request, 'Brand name is required.')
            return redirect('admin_brand_list')

        if Brand.objects.filter(brand_name__iexact=brand_name).exists():
            messages.error(request, f'Brand "{brand_name}" already exists.')
            return redirect('admin_brand_list')

        brand = Brand(
            brand_name = brand_name,
            slug       = _unique_slug(brand_name),
            status     = 'active',
        )

        cropped = save_cropped_image(image_data, 'photos/brands', 'brand')
        if cropped:
            brand.logo_image = cropped

        brand.save()
        messages.success(request, f'Brand "{brand_name}" added successfully.')

    return redirect('admin_brand_list')


@admin_required
def brand_edit(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)

    if request.method == 'POST':
        brand_name = request.POST.get('brand_name', '').strip()
        image_data = request.POST.get('logo_image', '')

        if not brand_name:
            messages.error(request, 'Brand name is required.')
            return redirect('admin_brand_list')

        if Brand.objects.filter(brand_name__iexact=brand_name).exclude(id=brand_id).exists():
            messages.error(request, f'Brand "{brand_name}" already exists.')
            return redirect('admin_brand_list')

        brand.brand_name = brand_name

        new_slug = slugify(brand_name)
        if new_slug != brand.slug:
            brand.slug = _unique_slug(brand_name, exclude_id=brand_id)

        cropped = save_cropped_image(image_data, 'photos/brands', 'brand')
        if cropped:
            brand.logo_image = cropped

        brand.save()
        messages.success(request, f'Brand updated to "{brand_name}" successfully.')

    return redirect('admin_brand_list')


@admin_required
@require_POST
def brand_toggle(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.status = 'inactive' if brand.status == 'active' else 'active'
    brand.save()

    messages.success(request, f'Brand "{brand.brand_name}" has been {brand.status} successfully.')
    return redirect('admin_brand_list')


def brand_suggestions(request):
    """AJAX endpoint — same pattern as store search_suggestions."""
    from django.http import JsonResponse
    q = request.GET.get('q', '').strip()
    suggestions = []
    if len(q) >= 2:
        suggestions = list(
            Brand.objects.filter(brand_name__icontains=q)
                         .values_list('brand_name', flat=True)
                         .order_by('brand_name')[:8]
        )
    return JsonResponse({'suggestions': suggestions})