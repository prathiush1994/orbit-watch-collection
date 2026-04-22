from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from carts.views import _get_or_create_cart
from carts.models import CartItem
from accounts.models import UserAddress
from .helpers import _compute_totals, _get_wallet, _razorpay_client, _build_order_from_session
from ..models import Payment
from decimal import Decimal


"""
Replace the checkout() function in your orders/views.py with this version.
It uses _compute_totals (which applies offer discounts first) and
passes annotated cart_items to the template so item.sub_total shows
the correct discounted price.

Also add this import at top of orders/views.py if not already there:
    from offers.utils import get_applicable_offer, apply_discount
"""
from decimal import Decimal


# ─────────────────────────────────────────────────────────────────────────────
# CHECKOUT PAGE
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def checkout(request):
    from offers.utils import get_applicable_offer, apply_discount

    cart       = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True
    ).select_related(
        'variant', 'variant__product'
    ).prefetch_related(
        'variant__product__category',
        'variant__product__offer',
        'variant__product__category__offer',
    )

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    # Annotate each item with its discounted sub_total for the template
    cart_items_list = list(cart_items)
    for item in cart_items_list:
        if item.variant.stock > 0:
            try:
                pct, _ = get_applicable_offer(item.variant.product)
                ep = apply_discount(item.variant.price, pct)
            except Exception:
                ep = Decimal(str(item.variant.price))
            item.sub_total = ep * item.quantity
        else:
            item.sub_total = Decimal('0')

    totals    = _compute_totals(cart_items_list, request.session)
    wallet    = _get_wallet(request.user)
    addresses = UserAddress.objects.filter(user=request.user).order_by('-is_default')

    context = {
        'cart_items'       : cart_items_list,
        'total'            : totals['subtotal'],
        'tax'              : totals['tax'],
        'grand_total'      : totals['grand_total'],
        'coupon_discount'  : totals['coupon_discount'],
        'coupon_code'      : totals['coupon_code'],
        'after_coupon'     : totals['after_coupon'],
        'referral_discount': totals['referral_discount'],
        'referral_code'    : totals['referral_code'],
        'after_referral'   : totals['after_referral'],
        'wallet_balance'   : wallet.balance,
        'wallet_used'      : totals['wallet_used'],
        'wallet_applied'   : totals['wallet_applied'],
        'final_total'      : totals['final_total'],
        'addresses'        : addresses,
        'razorpay_key_id'  : settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'orders/checkout.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# PLACE ORDER — also uses _compute_totals (offer-aware)
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def place_order(request):
    if request.method != 'POST':
        return redirect('checkout')

    cart       = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True
    ).select_related(
        'variant', 'variant__product'
    ).prefetch_related(
        'variant__product__category',
        'variant__product__offer',
        'variant__product__category__offer',
    )

    if not cart_items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')

    address_id = request.POST.get('address_id')
    if not address_id:
        messages.error(request, 'Please select a delivery address.')
        return redirect('checkout')
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)

    totals         = _compute_totals(list(cart_items), request.session)
    payment_method = request.POST.get('payment_method', 'COD')

    # Validate wallet
    if totals['wallet_used'] > 0:
        wallet = _get_wallet(request.user)
        if wallet.balance < totals['wallet_used']:
            messages.error(request, 'Wallet balance changed. Please review your order.')
            return redirect('checkout')

    if payment_method == 'COD':
        pay_method = 'WALLET' if totals['final_total'] == 0 else 'COD'
        payment = Payment.objects.create(
            user           = request.user,
            payment_method = pay_method,
            amount_paid    = str(totals['final_total']),
            status         = 'Completed' if totals['final_total'] == 0 else 'Pending',
        )
        order = _build_order_from_session(request, address, payment, totals)
        return redirect('order_complete', order_number=order.order_number)

    if payment_method == 'RAZORPAY':
        amount_paise = int(totals['final_total'] * 100)
        rz_client    = _razorpay_client()
        rz_order     = rz_client.order.create({
            'amount': amount_paise, 'currency': 'INR', 'payment_capture': 1,
        })
        request.session['pending_address_id']        = address_id
        request.session['pending_razorpay_order_id'] = rz_order['id']
        return render(request, 'orders/razorpay_payment.html', {
            'razorpay_key_id'  : settings.RAZORPAY_KEY_ID,
            'razorpay_order_id': rz_order['id'],
            'amount_paise'     : amount_paise,
            'final_total'      : totals['final_total'],
            'order_currency'   : 'INR',
            'user_name'        : f'{request.user.first_name} {request.user.last_name}'.strip() or request.user.email,
            'user_email'       : request.user.email,
            'user_phone'       : getattr(request.user, 'phone_number', ''),
        })

    messages.error(request, 'Invalid payment method.')
    return redirect('checkout')