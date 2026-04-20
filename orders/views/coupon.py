import json
from decimal import Decimal
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from ..models import Coupon, CouponUsage
from carts.views import _get_or_create_cart
from carts.models import CartItem
from .helpers import _compute_totals


@login_required(login_url='login')
def apply_coupon(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request.'})

    data        = json.loads(request.body)
    code        = data.get('code', '').strip().upper()
    #grand_total = Decimal(str(data.get('grand_total', '0')))
    cart = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(    cart=cart, is_active=True ).select_related('variant', 'variant__product')
    totals = _compute_totals(cart_items, request.session)
    grand_total = totals['grand_total']

    
    if request.session.get('coupon_code'):
        return JsonResponse({'success': False,
                             'message': 'A coupon is already applied. Remove it first.'})

    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid coupon code.'})

    valid, msg = coupon.is_valid()
    if not valid:
        return JsonResponse({'success': False, 'message': msg})

    if grand_total < coupon.min_order_amt:
        return JsonResponse({'success': False,
                             'message': f'Minimum order ₹{coupon.min_order_amt} required.'})

    usage, _ = CouponUsage.objects.get_or_create(coupon=coupon, user=request.user)
    if usage.used_count >= coupon.usage_limit:
        return JsonResponse({'success': False,
                             'message': 'You have already used this coupon.'})

    discount   = coupon.calculate_discount(grand_total)
    after_coup = max(round(grand_total - discount, 2), Decimal('0'))

    request.session['coupon_code']     = coupon.code
    request.session['coupon_id']       = coupon.id
    request.session['coupon_discount'] = str(discount)

    # Recalculate wallet if already applied
    wallet_used = Decimal(request.session.get('wallet_used', '0'))
    if wallet_used > 0:
        wallet_used = min(wallet_used, after_coup)
        request.session['wallet_used'] = str(wallet_used)

    final = max(after_coup - wallet_used, Decimal('0'))

    return JsonResponse({
        'success'   : True,
        'message'   : f'Coupon "{coupon.code}" applied! You saved ₹{discount}.',
        'discount'  : str(discount),
        'after_coup': str(after_coup),
        'final'     : str(final),
    })

@login_required(login_url='login')
def remove_coupon(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request.'})

    data        = json.loads(request.body)
    #grand_total = Decimal(str(data.get('grand_total', '0')))
    cart = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(    cart=cart, is_active=True ).select_related('variant', 'variant__product')
    totals = _compute_totals(cart_items, request.session)
    grand_total = totals['grand_total']

    request.session.pop('coupon_code', None)
    request.session.pop('coupon_id', None)
    request.session.pop('coupon_discount', None)

    wallet_used = Decimal(request.session.get('wallet_used', '0'))
    if wallet_used > 0:
        wallet_used = min(wallet_used, grand_total)
        request.session['wallet_used'] = str(wallet_used)

    final = max(grand_total - wallet_used, Decimal('0'))

    return JsonResponse({
        'success'   : True,
        'message'   : 'Coupon removed.',
        'after_coup': str(grand_total),
        'final'     : str(final),
    })

