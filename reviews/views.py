from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg

from store.models import ProductVariant
from orders.models import OrderProduct
from .models import Review
from .forms import ReviewForm


def _user_has_purchased(user, variant):
    """
    Returns True if the user has at least one Delivered order
    that contains this variant.
    """
    return OrderProduct.objects.filter(
        order__user=user,
        order__status='Delivered',
        variant=variant,
    ).exists()


@login_required
def submit_review(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id, is_available=True)
    redirect_url = variant.get_url()          # back to product page after submit

    # ── Verified purchase check ───────────────────────────────────────────────
    if not _user_has_purchased(request.user, variant):
        messages.error(request, "You can only review products you have purchased and received.")
        return redirect(redirect_url)

    # ── Prevent duplicate review ──────────────────────────────────────────────
    existing = Review.objects.filter(user=request.user, variant=variant).first()
    if existing:
        messages.warning(request, "You have already reviewed this product.")
        return redirect(redirect_url)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review         = form.save(commit=False)
            review.user    = request.user
            review.variant = variant
            review.save()
            messages.success(request, "Thank you! Your review has been posted.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)

    return redirect(redirect_url)


@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    redirect_url = review.variant.get_url()
    review.delete()
    messages.success(request, "Your review has been deleted.")
    return redirect(redirect_url)