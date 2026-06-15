from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from offers.models import ReferralCode
import random
import string
import re
import uuid
import base64
from django.core.files.base import ContentFile
from collections import Counter


@login_required(login_url="login")
def profile(request):
    user = request.user
    referral_code = None
    try:
        referral_code = user.referral_code
    except Exception:
        while True:
            code = "ORB" + "".join(
                random.choices(string.ascii_uppercase + string.digits, k=5)
            )
            if not ReferralCode.objects.filter(code=code).exists():
                break
        referral_code = ReferralCode.objects.create(
            user=user,
            code=code,
            referee_discount=300,
            referrer_reward=50,
        )
    times_used = (
        ReferralCode.objects.filter(user=user)
        .values_list("times_used", flat=True)
        .first()
        or 0
    )

    referral_url = f"{request.scheme}://{request.get_host()}/user/orbit-watch/register/?ref={referral_code.token}"
    referral_message = (
        f"Get ₹{referral_code.referee_discount} OFF on your first order at Orbit Watch Collection.\n\n"
        f"1. Create an account using the link below.\n"
        f"2. Apply the referral code during checkout of your first order.\n"
        f"3. Get ₹{referral_code.referee_discount} OFF instantly.\n\n"
        f"Referral Code: {referral_code.code}\n\n"
        f"Register Here:\n"
        f"{referral_url}"
    )

    return render(
        request,
        "dashboard/profile.html",
        {
            "referral_code": referral_code,
            "referral_message": referral_message,
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

        if not re.match(r"^[A-Za-z ]+$", user.first_name):
            messages.error(request, "First name must contain only letters.")
            return redirect("dashboard_edit_profile")

        if not re.match(r"^[A-Za-z ]+$", user.last_name):
            messages.error(request, "Last name must contain only letters.")
            return redirect("dashboard_edit_profile")

        if not user.phone_number.isdigit():
            messages.error(request, "Phone number must contain only digits.")
            return redirect("dashboard_edit_profile")

        if len(user.phone_number) != 10:
            messages.error(request, "Phone number must contain 10 digits.")
            return redirect("dashboard_edit_profile")

        counts = Counter(user.phone_number)
        if max(counts.values()) > 3:
            messages.error(request, "Enter a valid phone number")
            return redirect("dashboard_edit_profile")

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
