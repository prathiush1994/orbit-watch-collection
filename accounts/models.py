from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class MyAccountManager(BaseUserManager):
    def create_user(self, first_name, last_name, email, password=None):
        if not email:
            raise ValueError('User must have an email address')

        user = self.model(
            email=self.normalize_email(email),
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, first_name, last_name, email, password, **extra_fields):
        user = self.create_user(
            email=self.normalize_email(email),
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        user.is_admin       = True
        user.is_active      = True
        user.is_staff       = True
        user.is_superadmin  = True
        user.email_verified = True
        user.save(using=self._db)
        return user


class Account(AbstractBaseUser):
    first_name     = models.CharField(max_length=50)
    last_name      = models.CharField(max_length=50)
    email          = models.EmailField(max_length=100, unique=True)
    phone_number   = models.CharField(max_length=20, blank=True, null=True)
    profile_photo  = models.ImageField(upload_to='photos/profile', blank=True, null=True)
    email_verified = models.BooleanField(default=False)

    # OTP fields
    otp            = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    otp_purpose    = models.CharField(max_length=20, null=True, blank=True)
    # purposes: 'register' | 'forgot' | 'login' | 'change_password' | 'delete_account'

    date_joined    = models.DateTimeField(auto_now_add=True)
    last_login     = models.DateTimeField(auto_now=True)

    is_admin       = models.BooleanField(default=False)
    is_staff       = models.BooleanField(default=False)
    is_active      = models.BooleanField(default=False)
    is_superadmin  = models.BooleanField(default=False)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = MyAccountManager()

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_profile_photo(self):
        if self.profile_photo:
            return self.profile_photo.url
        return None

    class Meta:
        verbose_name        = 'Account'
        verbose_name_plural = 'Accounts'

class UserAddress(models.Model):
    ADDRESS_TYPE_CHOICES = (
        ('Home',  'Home'),
        ('Work',  'Work'),
        ('Other', 'Other'),
    )
    user         = models.ForeignKey(
                       'accounts.Account',
                       on_delete=models.CASCADE,
                       related_name='addresses'
                   )
    full_name    = models.CharField(max_length=100)
    phone        = models.CharField(max_length=20)
    address_line = models.TextField(max_length=300)
    city         = models.CharField(max_length=100)
    state        = models.CharField(max_length=100)
    pincode      = models.CharField(max_length=10)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, default='Home')
    is_default   = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        verbose_name        = 'User Address'
        verbose_name_plural = 'User Addresses'
        ordering            = ['-is_default', '-created_at']
 
    def __str__(self):
        return f"{self.full_name} — {self.city} ({self.address_type})"
 
    def save(self, *args, **kwargs):
        if self.is_default:
            UserAddress.objects.filter(
                user=self.user, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
 