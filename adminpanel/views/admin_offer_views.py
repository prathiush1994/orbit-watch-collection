from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.core.paginator import Paginator

from offers.models import ProductOffer, CategoryOffer, ReferralCode


def _get_products():
    from store.models import Product
    try:
        return Product.objects.filter(is_available=True).order_by('product_name')
    except Exception:
        from store.models import Product
        return Product.objects.all().order_by('product_name')


def _get_categories():
    from store.models import Category
    try:
        return Category.objects.filter(is_active=True).order_by('category_name')
    except Exception:
        from store.models import Category
        return Category.objects.all().order_by('category_name')


# ─────────────────────────────────────────────────────────
# OFFER LIST
# ─────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_offer_list(request):
    from accounts.models import Account
    from django.db.models import Prefetch

    now             = timezone.now()
    product_offers  = ProductOffer.objects.select_related('product').order_by('-id')
    category_offers = CategoryOffer.objects.select_related('category').order_by('-id')

    all_users = Account.objects.filter(
        is_staff=False, is_active=True
    ).prefetch_related(
        Prefetch('referral_code', queryset=ReferralCode.objects.all(), to_attr='_ref')
    ).order_by('-date_joined')

    paginator    = Paginator(all_users, 15)
    ref_page_obj = paginator.get_page(request.GET.get('ref_page', 1))

    return render(request, 'adminpanel/admin_offer_list.html', {
        'product_offers' : product_offers,
        'category_offers': category_offers,
        'ref_page_obj'   : ref_page_obj,
        'now'            : now,
        'active_tab'     : request.GET.get('tab', 'product'),
    })


# ─────────────────────────────────────────────────────────
# PRODUCT OFFER
# ─────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_product_offer_add(request):
    from store.models import Product
    products = _get_products()

    if request.method == 'POST':
        product_id   = request.POST.get('product_id', '').strip()
        discount_pct = request.POST.get('discount_pct', '').strip()
        is_active    = request.POST.get('is_active') == 'on'
        valid_from   = request.POST.get('valid_from', '').strip()
        valid_until  = request.POST.get('valid_until', '').strip() or None

        if not product_id:
            messages.error(request, 'Please select a product.')
            return render(request, 'adminpanel/admin_offer_product_form.html',
                          {'products': products, 'action': 'Add'})
        try:
            disc = float(discount_pct)
            if not (0 < disc <= 90):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Discount must be between 1 and 90.')
            return render(request, 'adminpanel/admin_offer_product_form.html',
                          {'products': products, 'action': 'Add'})

        product = get_object_or_404(Product, id=product_id)
        if ProductOffer.objects.filter(product=product).exists():
            messages.error(request, f'"{product.product_name}" already has an offer. Edit it instead.')
            return render(request, 'adminpanel/admin_offer_product_form.html',
                          {'products': products, 'action': 'Add'})

        ProductOffer.objects.create(
            product=product, discount_pct=disc, is_active=is_active,
            valid_from=valid_from or timezone.now(), valid_until=valid_until,
        )
        messages.success(request, f'Offer added for "{product.product_name}".')
        return redirect('admin_offer_list')

    return render(request, 'adminpanel/admin_offer_product_form.html',
                  {'products': products, 'action': 'Add'})


@staff_member_required(login_url='admin_login')
def admin_product_offer_edit(request, offer_id):
    offer    = get_object_or_404(ProductOffer, id=offer_id)
    products = _get_products()

    if request.method == 'POST':
        discount_pct = request.POST.get('discount_pct', '').strip()
        is_active    = request.POST.get('is_active') == 'on'
        valid_from   = request.POST.get('valid_from', '').strip()
        valid_until  = request.POST.get('valid_until', '').strip() or None
        try:
            disc = float(discount_pct)
            if not (0 < disc <= 90):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Discount must be between 1 and 90.')
            return render(request, 'adminpanel/admin_offer_product_form.html',
                          {'offer': offer, 'products': products, 'action': 'Edit'})

        offer.discount_pct = disc
        offer.is_active    = is_active
        if valid_from:
            offer.valid_from = valid_from
        offer.valid_until = valid_until
        offer.save()
        messages.success(request, 'Product offer updated.')
        return redirect('admin_offer_list')

    return render(request, 'adminpanel/admin_offer_product_form.html',
                  {'offer': offer, 'products': products, 'action': 'Edit'})


@staff_member_required(login_url='admin_login')
def admin_product_offer_toggle(request, offer_id):
    offer           = get_object_or_404(ProductOffer, id=offer_id)
    offer.is_active = not offer.is_active
    offer.save(update_fields=['is_active'])
    messages.success(request, f'Offer {"activated" if offer.is_active else "deactivated"}.')
    return redirect('admin_offer_list')


@staff_member_required(login_url='admin_login')
def admin_product_offer_delete(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)
    if request.method == 'POST':
        offer.delete()
        messages.success(request, 'Product offer deleted.')
    return redirect('admin_offer_list')


# ─────────────────────────────────────────────────────────
# CATEGORY OFFER
# ─────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_category_offer_add(request):
    from store.models import Category
    categories = _get_categories()

    if request.method == 'POST':
        category_id  = request.POST.get('category_id', '').strip()
        discount_pct = request.POST.get('discount_pct', '').strip()
        is_active    = request.POST.get('is_active') == 'on'
        valid_from   = request.POST.get('valid_from', '').strip()
        valid_until  = request.POST.get('valid_until', '').strip() or None

        if not category_id:
            messages.error(request, 'Please select a category.')
            return render(request, 'adminpanel/admin_offer_category_form.html',
                          {'categories': categories, 'action': 'Add'})
        try:
            disc = float(discount_pct)
            if not (0 < disc <= 90):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Discount must be between 1 and 90.')
            return render(request, 'adminpanel/admin_offer_category_form.html',
                          {'categories': categories, 'action': 'Add'})

        category = get_object_or_404(Category, id=category_id)
        if CategoryOffer.objects.filter(category=category).exists():
            messages.error(request, f'"{category.category_name}" already has an offer. Edit it instead.')
            return render(request, 'adminpanel/admin_offer_category_form.html',
                          {'categories': categories, 'action': 'Add'})

        CategoryOffer.objects.create(
            category=category, discount_pct=disc, is_active=is_active,
            valid_from=valid_from or timezone.now(), valid_until=valid_until,
        )
        messages.success(request, f'Offer added for "{category.category_name}".')
        return redirect('admin_offer_list')

    return render(request, 'adminpanel/admin_offer_category_form.html',
                  {'categories': categories, 'action': 'Add'})


@staff_member_required(login_url='admin_login')
def admin_category_offer_edit(request, offer_id):
    offer      = get_object_or_404(CategoryOffer, id=offer_id)
    categories = _get_categories()

    if request.method == 'POST':
        discount_pct = request.POST.get('discount_pct', '').strip()
        is_active    = request.POST.get('is_active') == 'on'
        valid_from   = request.POST.get('valid_from', '').strip()
        valid_until  = request.POST.get('valid_until', '').strip() or None
        try:
            disc = float(discount_pct)
            if not (0 < disc <= 90):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Discount must be between 1 and 90.')
            return render(request, 'adminpanel/admin_offer_category_form.html',
                          {'offer': offer, 'categories': categories, 'action': 'Edit'})

        offer.discount_pct = disc
        offer.is_active    = is_active
        if valid_from:
            offer.valid_from = valid_from
        offer.valid_until = valid_until
        offer.save()
        messages.success(request, 'Category offer updated.')
        return redirect('admin_offer_list')

    return render(request, 'adminpanel/admin_offer_category_form.html',
                  {'offer': offer, 'categories': categories, 'action': 'Edit'})


@staff_member_required(login_url='admin_login')
def admin_category_offer_toggle(request, offer_id):
    offer           = get_object_or_404(CategoryOffer, id=offer_id)
    offer.is_active = not offer.is_active
    offer.save(update_fields=['is_active'])
    messages.success(request, f'Category offer {"activated" if offer.is_active else "deactivated"}.')
    return redirect('admin_offer_list')


@staff_member_required(login_url='admin_login')
def admin_category_offer_delete(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    if request.method == 'POST':
        offer.delete()
        messages.success(request, 'Category offer deleted.')
    return redirect('admin_offer_list')

