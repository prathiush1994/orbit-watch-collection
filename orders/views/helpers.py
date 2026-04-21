import random
import string
from decimal import Decimal
import razorpay
from django.conf import settings
from carts.views import _get_or_create_cart
from carts.models import CartItem
from wallet.models import Wallet
from orders.models import Order, OrderProduct, Coupon, CouponUsage
from offers.models import ReferralCode, ReferralUse

def _generate_order_number():
    while True:
        number = 'ORB' + ''.join(random.choices(string.digits, k=8))
        if not Order.objects.filter(order_number=number).exists():
            return number

def _get_cart_id(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

def _get_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet

def _razorpay_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

def _build_order_from_session(request, address, payment_obj, totals):

    order = Order.objects.create(
        user         = request.user,
        payment      = payment_obj,
        full_name    = address.full_name,
        phone        = address.phone,
        address_line = address.address_line,
        city         = address.city,
        state        = address.state,
        pincode      = address.pincode,
        address_type = address.address_type,
        order_number = _generate_order_number(),
        order_total  = totals['final_total'],
        tax          = totals['tax'],
        discount     = totals['coupon_discount'],
        coupon_code  = totals['coupon_code'],
        wallet_used  = totals['wallet_used'],
        is_ordered   = True,
    )

    # Attach coupon FK + update usage counters
    if totals['coupon_id']:
        try:
            coupon_obj = Coupon.objects.get(id=totals['coupon_id'])
            order.coupon = coupon_obj
            order.save(update_fields=['coupon'])
            usage, _ = CouponUsage.objects.get_or_create(coupon=coupon_obj, user=request.user)
            usage.used_count += 1
            usage.save()
            coupon_obj.total_usage += 1
            coupon_obj.save(update_fields=['total_usage'])
        except Coupon.DoesNotExist:
            pass

    # Deduct wallet balance
    if totals['wallet_used'] > 0:
        wallet = _get_wallet(request.user)
        wallet.debit(
            amount      = totals['wallet_used'],
            description = f'Payment for Order #{order.order_number}',
            order       = order,
        )

    # Create order items + reduce stock
    cart = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True
    ).select_related('variant', 'variant__product')

    for item in cart_items:
        if item.variant.stock <= 0:
            continue
        OrderProduct.objects.create(
            order         = order,
            user          = request.user,
            variant       = item.variant,
            product_name  = item.variant.product.product_name,
            color_name    = item.variant.color_name,
            product_price = item.variant.price,
            quantity      = item.quantity,
            ordered       = True,
        )
        item.variant.stock -= item.quantity
        item.variant.save(update_fields=['stock'])

    # Clear cart
    cart_items.delete()

    # Clear session
    for key in ['coupon_code', 'coupon_id', 'coupon_discount',
                'wallet_used', 'wallet_applied',
                'pending_address_id', 'pending_razorpay_order_id']:
        request.session.pop(key, None)

    return order

def checkout_context_additions(totals):
    """Extra keys to add to checkout context."""
    return {
        'referral_discount': totals['referral_discount'],
        'referral_code'    : totals['referral_code'],
        'after_referral'   : totals['after_referral'],
    }

def _build_order_from_session(request, address, payment_obj, totals):

    order = Order.objects.create(
        user         = request.user,
        payment      = payment_obj,
        full_name    = address.full_name,
        phone        = address.phone,
        address_line = address.address_line,
        city         = address.city,
        state        = address.state,
        pincode      = address.pincode,
        address_type = address.address_type,
        order_number = _generate_order_number(),
        order_total  = totals['final_total'],
        tax          = totals['tax'],
        discount     = totals['coupon_discount'] + totals['referral_discount'],
        coupon_code  = totals['coupon_code'],
        wallet_used  = totals['wallet_used'],
        is_ordered   = True,
    )

    # ── Coupon usage ──────────────────────────────────
    if totals['coupon_id']:
        try:
            coupon_obj = Coupon.objects.get(id=totals['coupon_id'])
            order.coupon = coupon_obj
            order.save(update_fields=['coupon'])
            usage, _ = CouponUsage.objects.get_or_create(coupon=coupon_obj, user=request.user)
            usage.used_count += 1
            usage.save()
            coupon_obj.total_usage += 1
            coupon_obj.save(update_fields=['total_usage'])
        except Coupon.DoesNotExist:
            pass

    # ── Referral: lock it (one-time use) + reward referrer ──
    if totals['referral_id']:
        try:
            ref_code = ReferralCode.objects.get(id=totals['referral_id'])

            # Create ReferralUse to lock this code for this user (one-time)
            ReferralUse.objects.get_or_create(
                referral_code = ref_code,
                referee       = request.user,
                defaults      = {'reward_given': True},
            )

            # Credit the REFERRER's wallet immediately
            referrer_wallet, _ = Wallet.objects.get_or_create(user=ref_code.user)
            referrer_wallet.credit(
                amount      = ref_code.referrer_reward,
                description = f'Referral reward — {request.user.email} placed first order '
                              f'using your code {ref_code.code}',
                order       = order,
            )

            # Increment times_used
            ref_code.times_used += 1
            ref_code.save(update_fields=['times_used'])

        except (ReferralCode.DoesNotExist, Exception):
            pass  # never block order creation for referral errors

    # ── Wallet debit ──────────────────────────────────
    if totals['wallet_used'] > 0:
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        wallet.debit(
            amount      = totals['wallet_used'],
            description = f'Payment for Order #{order.order_number}',
            order       = order,
        )

    # ── Order items + stock ───────────────────────────
    cart = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True
    ).select_related('variant', 'variant__product')

    for item in cart_items:
        if item.variant.stock <= 0:
            continue
        OrderProduct.objects.create(
            order         = order,
            user          = request.user,
            variant       = item.variant,
            product_name  = item.variant.product.product_name,
            color_name    = item.variant.color_name,
            product_price = item.variant.price,
            quantity      = item.quantity,
            ordered       = True,
        )
        item.variant.stock -= item.quantity
        item.variant.save(update_fields=['stock'])

    cart_items.delete()

    # ── Clear session ─────────────────────────────────
    for key in ['coupon_code', 'coupon_id', 'coupon_discount',
                'referral_code', 'referral_id', 'referral_discount',
                'wallet_used', 'wallet_applied',
                'pending_address_id', 'pending_razorpay_order_id']:
        request.session.pop(key, None)

    return order

def _compute_totals(cart_items, session):
    """
    Compute order totals server-side.
    Order of deductions:
      1. Offer discount   (per-item, baked into subtotal)
      2. Coupon discount  (% or fixed off subtotal+tax)
      3. Referral discount
      4. Wallet
    """
    from offers.utils import get_applicable_offer, apply_discount

    subtotal = Decimal('0')
    for item in cart_items:
        if item.variant.stock <= 0:
            continue
        # Use discounted price if offer exists
        try:
            pct, _, _ = get_applicable_offer(item.variant.product)
            ep = apply_discount(item.variant.price, pct)
        except Exception:
            ep = item.variant.price
        subtotal += ep * item.quantity

    tax         = round(Decimal('0.18') * subtotal, 2)
    grand_total = round(subtotal + tax, 2)

    coupon_discount   = Decimal(session.get('coupon_discount', '0'))
    coupon_code       = session.get('coupon_code', '')
    coupon_id         = session.get('coupon_id')
    after_coupon      = round(grand_total - coupon_discount, 2)

    referral_discount = Decimal(session.get('referral_discount', '0'))
    referral_code     = session.get('referral_code', '')
    referral_id       = session.get('referral_id')
    after_referral    = round(after_coupon - referral_discount, 2)

    wallet_used       = Decimal(session.get('wallet_used', '0'))
    wallet_applied    = session.get('wallet_applied', False)
    final_total       = max(round(after_referral - wallet_used, 2), Decimal('0'))

    return {
        'subtotal'         : subtotal,
        'tax'              : tax,
        'grand_total'      : grand_total,
        'coupon_discount'  : coupon_discount,
        'coupon_code'      : coupon_code,
        'coupon_id'        : coupon_id,
        'after_coupon'     : after_coupon,
        'referral_discount': referral_discount,
        'referral_code'    : referral_code,
        'referral_id'      : referral_id,
        'after_referral'   : after_referral,
        'wallet_used'      : wallet_used,
        'wallet_applied'   : wallet_applied,
        'final_total'      : final_total,
    }