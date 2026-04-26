from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from offers.models import ReferralCode
import random, string
import uuid
import base64
from django.core.files.base import ContentFile


@login_required(login_url="login")
def profile(request):
    user = request.user

    # Auto-generate referral code on first profile visit
    referral_code = None
    try:
        referral_code = user.referral_code
    except Exception:
        # User has no code yet — create one now
        while True:
            code = "ORB" + "".join(
                random.choices(string.ascii_uppercase + string.digits, k=5)
            )
            if not ReferralCode.objects.filter(code=code).exists():
                break
        referral_code = ReferralCode.objects.create(
            user=user,
            code=code,
            referee_discount=100,  # ₹100 wallet credit for new user
            referrer_reward=50,  # ₹50 wallet reward for referrer
        )

    # Stats: how many people used this code
    times_used = (
        ReferralCode.objects.filter(user=user)
        .values_list("times_used", flat=True)
        .first()
        or 0
    )

    referral_url = f"{request.scheme}://{request.get_host()}/accounts/register/?ref={referral_code.token}"

    return render(
        request,
        "dashboard/profile.html",
        {
            "referral_code": referral_code,
            "referral_url": referral_url,
            "times_used": times_used,
        },
    )


@login_required(login_url="login")
def edit_profile(request):
    if request.method == "POST":
        user = request.user
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name = request.POST.get("last_name", "").strip()
        user.phone_number = request.POST.get("phone_number", "").strip()

        # Handle photo delete
        if request.POST.get("delete_photo") == "1":
            if user.profile_photo:
                user.profile_photo.delete(save=False)
                user.profile_photo = None

        # Handle cropped photo (base64 from JS cropper)
        cropped_photo = request.POST.get("cropped_photo", "").strip()
        if cropped_photo and cropped_photo.startswith("data:image"):
            try:
                format, imgstr = cropped_photo.split(";base64,")
                ext = format.split("/")[-1]
                filename = f"profile_{uuid.uuid4().hex}.{ext}"
                decoded = base64.b64decode(imgstr)
                user.profile_photo.save(filename, ContentFile(decoded), save=False)
            except Exception:
                pass

        user.save()
        messages.success(
            request, "Profile updated successfully.", extra_tags="edit_profile"
        )
        return redirect("dashboard_profile")

    return render(request, "dashboard/edit_profile.html")

