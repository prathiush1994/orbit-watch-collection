from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from store.models import Product, ProductVariant, VariantImage
from category.models import Category
from brands.models import Brand
from adminpanel.utils import save_cropped_image

from .decorators import admin_required


def _unique_slug_product(name, exclude_id=None):
    base = slugify(name)
    slug = base
    qs   = Product.objects.all()
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    counter = 1
    while qs.filter(slug=slug).exists():
        slug = f'{base}-{counter}'
        counter += 1
    return slug


def _unique_slug_variant(color_name, exclude_id=None):
    base = slugify(color_name)
    slug = base
    qs   = ProductVariant.objects.all()
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    counter = 1
    while qs.filter(slug=slug).exists():
        slug = f'{base}-{counter}'
        counter += 1
    return slug


# ── Product List ──────────────────────────────────────────────────────────────

@admin_required
def product_list(request):
    search_query = request.GET.get('q', '').strip()

    products = Product.objects.prefetch_related(
        'variants', 'category'
    ).select_related('brand').order_by('-created_at')

    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query) |
            Q(brand__brand_name__icontains=search_query)
        )

    paginator = Paginator(products, 15)
    page      = request.GET.get('page', 1)
    products  = paginator.get_page(page)

    all_product_names = Product.objects.values_list(
        'product_name', flat=True
    ).order_by('product_name')

    context = {
        'products'          : products,
        'search_query'      : search_query,
        'all_product_names' : all_product_names,
    }
    return render(request, 'adminpanel/products.html', context)


def product_suggestions(request):
    q = request.GET.get('q', '').strip()
    suggestions = []
    if len(q) >= 2:
        suggestions = list(
            Product.objects.filter(product_name__icontains=q)
                           .values_list('product_name', flat=True)
                           .order_by('product_name')[:8]
        )
    return JsonResponse({'suggestions': suggestions})


# ── Add / Edit Product ────────────────────────────────────────────────────────

@admin_required
def product_add(request):
    categories = Category.objects.filter(status='active').order_by('category_name')
    brands     = Brand.objects.filter(status='active').order_by('brand_name')

    if request.method == 'POST':
        name        = request.POST.get('product_name', '').strip()
        description = request.POST.get('description', '').strip()
        brand_id    = request.POST.get('brand', '')
        cat_ids     = request.POST.getlist('category')

        if not name:
            messages.error(request, 'Product name is required.')
            return render(request, 'adminpanel/product_form.html', {
                'categories': categories, 'brands': brands, 'is_edit': False
            })

        if Product.objects.filter(product_name__iexact=name).exists():
            messages.error(request, f'Product "{name}" already exists.')
            return render(request, 'adminpanel/product_form.html', {
                'categories': categories, 'brands': brands, 'is_edit': False
            })

        product = Product(
            product_name = name,
            slug         = _unique_slug_product(name),
            description  = description,
        )
        if brand_id:
            product.brand = get_object_or_404(Brand, id=brand_id)
        product.save()

        if cat_ids:
            product.category.set(cat_ids)

        messages.success(request, f'Product "{name}" added. Now add variants below.')
        return redirect('admin_product_edit', product_id=product.id)

    return render(request, 'adminpanel/product_form.html', {
        'categories' : categories,
        'brands'     : brands,
        'is_edit'    : False,
    })


@admin_required
def product_edit(request, product_id):
    product    = get_object_or_404(Product, id=product_id)
    categories = Category.objects.filter(status='active').order_by('category_name')
    brands     = Brand.objects.filter(status='active').order_by('brand_name')
    variants   = product.variants.prefetch_related('images').order_by('color_name')

    if request.method == 'POST':
        name        = request.POST.get('product_name', '').strip()
        description = request.POST.get('description', '').strip()
        brand_id    = request.POST.get('brand', '')
        cat_ids     = request.POST.getlist('category')

        if not name:
            messages.error(request, 'Product name is required.')
        elif Product.objects.filter(
            product_name__iexact=name
        ).exclude(id=product_id).exists():
            messages.error(request, f'Product "{name}" already exists.')
        else:
            product.product_name = name
            product.description  = description
            new_slug = slugify(name)
            if new_slug != product.slug:
                product.slug = _unique_slug_product(name, exclude_id=product_id)
            product.brand = get_object_or_404(Brand, id=brand_id) if brand_id else None
            product.save()
            product.category.set(cat_ids)
            messages.success(request, f'Product "{name}" updated successfully.')
            return redirect('admin_product_edit', product_id=product_id)

    context = {
        'product'    : product,
        'categories' : categories,
        'brands'     : brands,
        'variants'   : variants,
        'is_edit'    : True,
        'selected_categories': list(product.category.values_list('id', flat=True)),
    }
    return render(request, 'adminpanel/product_form.html', context)


# ── Add / Edit Variant ────────────────────────────────────────────────────────

@admin_required
def variant_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        color_name  = request.POST.get('color_name', '').strip()
        color_code  = request.POST.get('color_code', '').strip()
        price       = request.POST.get('price', '').strip()
        stock       = request.POST.get('stock', '0').strip()
        desc_override = request.POST.get('description_override', '').strip()
        is_available  = request.POST.get('is_available') == 'on'
        image_data    = request.POST.get('primary_image', '')

        if not color_name or not price:
            messages.error(request, 'Color name and price are required.')
        elif ProductVariant.objects.filter(
            product=product, color_name__iexact=color_name
        ).exists():
            messages.error(request, f'Variant "{color_name}" already exists for this product.')
        else:
            variant = ProductVariant(
                product              = product,
                color_name           = color_name,
                color_code           = color_code,
                price                = int(price),
                stock                = int(stock),
                description_override = desc_override,
                is_available         = is_available,
                slug                 = _unique_slug_variant(
                    f'{product.slug}-{color_name}'
                ),
            )
            cropped = save_cropped_image(image_data, 'photos/variants', 'variant')
            if cropped:
                variant.primary_image = cropped
            variant.save()


            # SAVE GALLERY IMAGES
            images = request.FILES.getlist('gallery_images')
            for img in images:
                VariantImage.objects.create(
                    variant=variant,
                    image=img
                )

            messages.success(request, f'Variant "{color_name}" added successfully.')
            return redirect('admin_product_edit', product_id=product_id)

    context = {
        'product'  : product,
        'is_edit'  : False,
    }
    return render(request, 'adminpanel/variant_form.html', context)


@admin_required
def variant_edit(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product = variant.product

    if request.method == 'POST':
        color_name    = request.POST.get('color_name', '').strip()
        color_code    = request.POST.get('color_code', '').strip()
        price         = request.POST.get('price', '').strip()
        stock         = request.POST.get('stock', '0').strip()
        desc_override = request.POST.get('description_override', '').strip()
        is_available  = request.POST.get('is_available') == 'on'
        image_data    = request.POST.get('primary_image', '')

        if not color_name or not price:
            messages.error(request, 'Color name and price are required.')
        elif ProductVariant.objects.filter(
            product=product, color_name__iexact=color_name
        ).exclude(id=variant_id).exists():
            messages.error(request, f'Variant "{color_name}" already exists.')
        else:
            variant.color_name           = color_name
            variant.color_code           = color_code
            variant.price                = int(price)
            variant.stock                = int(stock)
            variant.description_override = desc_override
            variant.is_available         = is_available

            cropped = save_cropped_image(image_data, 'photos/variants', 'variant')
            if cropped:
                variant.primary_image = cropped
            variant.save()

            # SAVE NEW GALLERY IMAGES
            images = request.FILES.getlist('gallery_images')
            for img in images:
                VariantImage.objects.create(
                    variant=variant,
                    image=img
                )

            messages.success(request, f'Variant "{color_name}" updated.')
            return redirect('admin_product_edit', product_id=product.id)

    context = {
        'product' : product,
        'variant' : variant,
        'is_edit' : True,
    }
    return render(request, 'adminpanel/variant_form.html', context)


# ── Gallery Images ────────────────────────────────────────────────────────────

@admin_required
def variant_image_add(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if request.method == 'POST':
        image_data = request.POST.get('gallery_image', '')
        if image_data:
            content = save_cropped_image(image_data, 'photos/variant_gallery', 'gallery')
            if content:
                VariantImage.objects.create(variant=variant, image=content)
                messages.success(request, 'Gallery image added.')
            else:
                messages.error(request, 'Invalid image data.')
        else:
            messages.error(request, 'No image provided.')

    return redirect('admin_product_edit', product_id=variant.product.id)


@admin_required
@require_POST
def variant_image_delete(request, image_id):
    img = get_object_or_404(VariantImage, id=image_id)
    product_id = img.variant.product.id
    img.image.delete(save=False)
    img.delete()
    messages.success(request, 'Gallery image removed.')
    return redirect('admin_product_edit', product_id=product_id)


def product_variants(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    variants = ProductVariant.objects.filter(product=product).order_by('-id')

    paginator = Paginator(variants, 10)
    page = request.GET.get('page')
    variants = paginator.get_page(page)

    context = {
        'product': product,
        'variants': variants
    }

    return render(request, 'adminpanel/variant_view.html', context)