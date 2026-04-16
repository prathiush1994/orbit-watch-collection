from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone

from offers.models import ProductOffer, CategoryOffer, ReferralCode, ReferralUse
from store.models import Product, Category


# ─────────────────────────────────────────────────────────
# OFFER DASHBOARD — lists all three offer types
# ─────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_offer_list(request):
    now              = timezone.now()
    product_offers   = ProductOffer.objects.select_related('product').order_by('-id')
    category_offers  = CategoryOffer.objects.select_related('category').order_by('-id')
    referral_codes   = ReferralCode.objects.select_related('user').order_by('-id')[:20]

    return render(request, 'adminpanel/admin_offer_list.html', {
        'product_offers' : product_offers,
        'category_offers': category_offers,
        'referral_codes' : referral_codes,
        'now'            : now,
    })


# ─────────────────────────────────────────────────────────
# PRODUCT OFFER — ADD
# ─────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_product_offer_add(request):
    products = Product.objects.filter(is_available=True).order_by('product_name')

    if request.method == 'POST':
        product_id   = request.POST.get('product_id')
        discount_pct = request.POST.get('discount_pct', '0')
        is_active    = request.POST.get('is_active') == 'on'
        valid_from   = request.POST.get('valid_from') or timezone.now()
        valid_until  = request.POST.get('valid_until') or None

        if not product_id:
            messages.error(request, 'Please select a product.')
            return render(request, 'adminpanel/admin_offer_product_form.html',
                          {'products': products, 'action': 'Add'})

        product = get_object_or_404(Product, id=product_id)

        if ProductOffer.objects.filter(product=product).exists():
            messages.error(request, f'"{product.product_name}" already has an offer. Edit it instead.')
            return redirect('admin_offer_list')

        try:
            disc = float(discount_pct)
            if not (0 < disc <= 90):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Discount must be between 1 and 90.')
            return render(request, 'adminpanel/admin_offer_product_form.html',
                          {'products': products, 'action': 'Add'})

        ProductOffer.objects.create(
            product=product, discount_pct=discount_pct,
            is_active=is_active, valid_from=valid_from, valid_until=valid_until,
        )
        messages.success(request, f'Offer added for "{product.product_name}".')
        return redirect('admin_offer_list')

    return render(request, 'adminpanel/admin_offer_product_form.html',
                  {'products': products, 'action': 'Add'})


# ─────────────────────────────────────────────────────────
# PRODUCT OFFER — EDIT
# ─────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_product_offer_edit(request, offer_id):
    offer    = get_object_or_404(ProductOffer, id=offer_id)
    products = Product.objects.filter(is_available=True).order_by('product_name')

    if request.method == 'POST':
        discount_pct = request.POST.get('discount_pct', '0')
        is_active    = request.POST.get('is_active') == 'on'
        valid_from   = request.POST.get('valid_from') or offer.valid_from
        valid_until  = request.POST.get('valid_until') or None

        try:
            disc = float(discount_pct)
            if not (0 < disc <= 90):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Discount must be between 1 and 90.')
            return render(request, 'adminpanel/admin_offer_product_form.html',
                          {'offer': offer, 'products': products, 'action': 'Edit'})

        offer.discount_pct = discount_pct
        offer.is_active    = is_active
        offer.valid_from   = valid_from
        offer.valid_until  = valid_until
        offer.save()
        messages.success(request, f'Product offer updated.')
        return redirect('admin_offer_list')

    return render(request, 'adminpanel/admin_offer_product_form.html',
                  {'offer': offer, 'products': products, 'action': 'Edit'})


# ─────────────────────────────────────────────────────────
# PRODUCT OFFER — TOGGLE / DELETE
# ─────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_product_offer_toggle(request, offer_id):
    offer           = get_object_or_404(ProductOffer, id=offer_id)
    offer.is_active = not offer.is_active
    offer.save(update_fields=['is_active'])
    state = 'activated' if offer.is_active else 'deactivated'
    messages.success(request, f'Offer {state}.')
    return redirect('admin_offer_list')


@staff_member_required(login_url='admin_login')
def admin_product_offer_delete(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)
    if request.method == 'POST':
        offer.delete()
        messages.success(request, 'Product offer deleted.')
    return redirect('admin_offer_list')


# ─────────────────────────────────────────────────────────
# CATEGORY OFFER — ADD
# ─────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_category_offer_add(request):
    categories = Category.objects.filter(is_active=True).order_by('category_name')

    if request.method == 'POST':
        category_id  = request.POST.get('category_id')
        discount_pct = request.POST.get('discount_pct', '0')
        is_active    = request.POST.get('is_active') == 'on'
        valid_from   = request.POST.get('valid_from') or timezone.now()
        valid_until  = request.POST.get('valid_until') or None

        if not category_id:
            messages.error(request, 'Please select a category.')
            return render(request, 'adminpanel/admin_offer_category_form.html',
                          {'categories': categories, 'action': 'Add'})

        category = get_object_or_404(Category, id=category_id)

        if CategoryOffer.objects.filter(category=category).exists():
            messages.error(request, f'"{category.category_name}" already has an offer.')
            return redirect('admin_offer_list')

        try:
            disc = float(discount_pct)
            if not (0 < disc <= 90):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Discount must be between 1 and 90.')
            return render(request, 'adminpanel/admin_offer_category_form.html',
                          {'categories': categories, 'action': 'Add'})

        CategoryOffer.objects.create(
            category=category, discount_pct=discount_pct,
            is_active=is_active, valid_from=valid_from, valid_until=valid_until,
        )
        messages.success(request, f'Offer added for category "{category.category_name}".')
        return redirect('admin_offer_list')

    return render(request, 'adminpanel/admin_offer_category_form.html',
                  {'categories': categories, 'action': 'Add'})


# ─────────────────────────────────────────────────────────
# CATEGORY OFFER — EDIT / TOGGLE / DELETE
# ─────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_category_offer_edit(request, offer_id):
    offer      = get_object_or_404(CategoryOffer, id=offer_id)
    categories = Category.objects.filter(is_active=True).order_by('category_name')

    if request.method == 'POST':
        discount_pct = request.POST.get('discount_pct', '0')
        is_active    = request.POST.get('is_active') == 'on'
        valid_from   = request.POST.get('valid_from') or offer.valid_from
        valid_until  = request.POST.get('valid_until') or None

        try:
            disc = float(discount_pct)
            if not (0 < disc <= 90):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Discount must be between 1 and 90.')
            return render(request, 'adminpanel/admin_offer_category_form.html',
                          {'offer': offer, 'categories': categories, 'action': 'Edit'})

        offer.discount_pct = discount_pct
        offer.is_active    = is_active
        offer.valid_from   = valid_from
        offer.valid_until  = valid_until
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


# ─────────────────────────────────────────────────────────
# REFERRAL — GENERATE code for a user
# ─────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_referral_generate(request):
    from accounts.models import Account
    import random, string

    if request.method == 'POST':
        user_id          = request.POST.get('user_id')
        referee_discount = request.POST.get('referee_discount', '100')
        referrer_reward  = request.POST.get('referrer_reward', '50')

        if not user_id:
            messages.error(request, 'Select a user.')
            return redirect('admin_offer_list')

        user = get_object_or_404(Account, id=user_id)

        if hasattr(user, 'referral_code'):
            messages.warning(request, f'{user.email} already has a referral code.')
            return redirect('admin_offer_list')

        # Generate unique 8-char code
        while True:
            code = 'ORB' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            if not ReferralCode.objects.filter(code=code).exists():
                break

        ReferralCode.objects.create(
            user=user, code=code,
            referee_discount=referee_discount,
            referrer_reward=referrer_reward,
        )
        messages.success(request, f'Referral code {code} generated for {user.email}.')
    return redirect('admin_offer_list')