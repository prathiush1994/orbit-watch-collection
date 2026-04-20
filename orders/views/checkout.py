from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from carts.views import _get_or_create_cart
from carts.models import CartItem
from accounts.models import UserAddress
from .helpers import _compute_totals, _get_wallet, _razorpay_client, _build_order_from_session
from ..models import Payment



@login_required(login_url='login')
def checkout(request):
    cart       = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True
    ).select_related('variant', 'variant__product')

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    totals    = _compute_totals(cart_items, request.session)
    wallet    = _get_wallet(request.user)
    addresses = UserAddress.objects.filter(user=request.user).order_by('-is_default')

    context = {
        'cart_items'     : cart_items,
        'total'          : totals['subtotal'],
        'tax'            : totals['tax'],
        'grand_total'    : totals['grand_total'],
        'coupon_discount': totals['coupon_discount'],
        'coupon_code'    : totals['coupon_code'],
        'after_coupon'   : totals['after_coupon'],
        'wallet_balance' : wallet.balance,
        'wallet_used'    : totals['wallet_used'],
        'wallet_applied' : totals['wallet_applied'],
        'final_total'    : totals['final_total'],
        'addresses'      : addresses,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'orders/checkout.html', context)

@login_required(login_url='login')
def place_order(request):
    if request.method != 'POST':
        return redirect('checkout')

    cart       = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True
    ).select_related('variant', 'variant__product')

    if not cart_items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')

    address_id = request.POST.get('address_id')
    if not address_id:
        messages.error(request, 'Please select a delivery address.')
        return redirect('checkout')
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)

    totals         = _compute_totals(cart_items, request.session)
    payment_method = request.POST.get('payment_method', 'COD')

    # Validate wallet balance hasn't changed between page load and submit
    if totals['wallet_used'] > 0:
        wallet = _get_wallet(request.user)
        if wallet.balance < totals['wallet_used']:
            messages.error(request, 'Your wallet balance changed. Please review your order.')
            return redirect('checkout')

    # ── COD PATH ─────────────────────────────────────────
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

    # ── RAZORPAY PATH ─────────────────────────────────────
    if payment_method == 'RAZORPAY':
        amount_paise = int(totals['final_total'] * 100)  # Razorpay uses paise (₹1 = 100 paise)
        rz_client    = _razorpay_client()
        rz_order     = rz_client.order.create({
            'amount'         : amount_paise,
            'currency'       : 'INR',
            'payment_capture': 1,          # auto-capture on success
        })

        # Store pending details in session — used after payment callback
        request.session['pending_address_id']        = address_id
        request.session['pending_razorpay_order_id'] = rz_order['id']

        context = {
            'razorpay_key_id'  : settings.RAZORPAY_KEY_ID,
            'razorpay_order_id': rz_order['id'],
            'amount_paise'     : amount_paise,
            'final_total'      : totals['final_total'],
            'order_currency'   : 'INR',
            'user_name'        : f'{request.user.first_name} {request.user.last_name}'.strip()
                                  or request.user.email,
            'user_email'       : request.user.email,
            'user_phone'       : getattr(request.user, 'phone_number', ''),
        }
        return render(request, 'orders/razorpay_payment.html', context)
    messages.error(request, 'Invalid payment method selected.')
    """
    variant = order_item.variant
    inv = variant.inventory
    inv.deduct_stock(
        qty=order_item.quantity,
        reason='order',
        updated_by=None,   # or request.user if available
        note=f"Order #{order.id}"
    )
    # Credit referrer reward on first order
    try:
        ref_use = request.user.used_referral
        if not ref_use.reward_given:
            from offers.models import ReferralCode
            ref_code = ref_use.referral_code
            if ref_code.is_active:
                from wallet.models import Wallet
                wallet, _ = Wallet.objects.get_or_create(user=ref_code.user)
                wallet.credit(
                    amount=ref_code.referrer_reward,
                    description=f'Referral reward — {request.user.email} placed first order',
                    order=order,
                )
                ref_use.reward_given = True
                ref_use.save(update_fields=['reward_given'])
                ref_code.times_used += 1
                ref_code.save(update_fields=['times_used'])
    except Exception:
        pass   # user has no referral, skip silently
    """
    return redirect('checkout')

