from django.core.mail import send_mail
from django.conf import settings
import random


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_email(email, otp, purpose='register'):
    subjects = {
        'register':        'Verify Your Email – Orbit Watch Collection',
        'forgot':          'Reset Your Password – Orbit Watch Collection',
        'login':           'Your Login OTP – Orbit Watch Collection',
        'change_password': 'Change Password OTP – Orbit Watch Collection',
        'delete_account':  'Account Deletion OTP – Orbit Watch Collection',
    }
    subject = subjects.get(purpose, 'OTP Code – Orbit Watch Collection')

    message = (
        f"Hello,\n\n"
        f"Your OTP code is: {otp}\n\n"
        f"This code will expire in 5 minutes.\n\n"
        f"If you didn't request this, please ignore this email.\n\n"
        f"Orbit Watch Collection Team"
    )

    html_message = f"""
    <html>
    <body style="font-family:Arial,sans-serif;padding:20px;background:#f9f9f9;">
      <div style="max-width:480px;margin:auto;background:#fff;border-radius:8px;padding:32px;">
        <h2 style="color:#FF6B00;">Orbit Watch Collection</h2>
        <p>Hello,</p>
        <p>Your OTP code is:</p>
        <h1 style="color:#FF6B00;letter-spacing:8px;font-size:40px;">{otp}</h1>
        <p style="color:#666;">This code will expire in <strong>5 minutes</strong>.</p>
        <p style="color:#999;font-size:12px;">If you didn't request this, ignore this email.</p>
        <hr style="border:1px solid #eee;">
        <p style="color:#999;font-size:12px;">Orbit Watch Collection Team</p>
      </div>
    </body>
    </html>
    """

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {email}: {e}")
        return False


def send_welcome_email(email, name):
    subject = 'Welcome to Orbit Watch Collection!'
    message = (
        f"Hello {name},\n\n"
        f"Welcome to Orbit Watch Collection! Your account is now active.\n\n"
        f"Happy shopping!\n\nOrbit Watch Collection Team"
    )
    html_message = f"""
    <html>
    <body style="font-family:Arial,sans-serif;padding:20px;background:#f9f9f9;">
      <div style="max-width:480px;margin:auto;background:#fff;border-radius:8px;padding:32px;">
        <h2 style="color:#FF6B00;">Welcome, {name}! 🎉</h2>
        <p>Your account has been successfully created.</p>
        <p>You can now browse our collection of premium watches.</p>
        <p>Happy shopping!</p>
        <hr style="border:1px solid #eee;">
        <p style="color:#999;font-size:12px;">Orbit Watch Collection Team</p>
      </div>
    </body>
    </html>
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        print(f"⚠️ Welcome email failed: {e}")