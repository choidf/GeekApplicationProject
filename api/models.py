from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from rest_framework.exceptions import ValidationError


class Category(models.Model):
    category = models.CharField(max_length=255)

class Brand(models.Model):
    brand = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

class Warranty(models.Model):
    warrant_period = models.IntegerField()
    description = models.TextField(null=True, blank=True)

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    warranty = models.ForeignKey(Warranty, on_delete=models.SET_NULL, null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    model = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    size_guide = models.TextField(null=True, blank=True)
    product_image = models.BinaryField(null=True, blank=True)
    like_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class SizeProduct(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=50)

class ColorProduct(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    color = models.CharField(max_length=50)

class Price(models.Model):
    size = models.ForeignKey(SizeProduct, on_delete=models.CASCADE)
    color = models.ForeignKey(ColorProduct, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=15, decimal_places=0)
    created_at = models.DateTimeField(auto_now_add=True)

class Discount(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()

class Address(models.Model):
    province = models.CharField(max_length=255)
    district = models.CharField(max_length=255)
    commune = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    housing_type = models.CharField(max_length=255)

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError('Username is required')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

class User(AbstractBaseUser, PermissionsMixin):
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    gender = models.CharField(max_length=50)
    is_superuser = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['emaixl']

class Voucher(models.Model):
    description = models.TextField(null=True, blank=True)
    discount_percent = models.DecimalField(max_digits=15, decimal_places=0, null=True, blank=True)
    discount_flat = models.DecimalField(max_digits=15, decimal_places=0, null=True, blank=True)
    max_discount = models.DecimalField(max_digits=15, decimal_places=0, null=True, blank=True)
    visible = models.BooleanField(default=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()

    def clean(self):
        """Validate that either discount_percent or discount_flat must be 0, but not both."""
        if self.discount_percent == 0 and self.discount_flat == 0:
            raise ValidationError("Either discount_percent or discount_flat must be greater than 0.")

        if self.discount_percent > 0 and self.discount_flat > 0:
            raise ValidationError("Only one of discount_percent or discount_flat should be greater than 0, not both.")

    def save(self, *args, **kwargs):
        """Ensure validation runs before saving the model."""
        self.clean()
        super().save(*args, **kwargs)

class Store(models.Model):
    address = models.CharField(max_length=255)

class Stock(models.Model):
    color = models.ForeignKey(ColorProduct, on_delete=models.CASCADE)
    size = models.ForeignKey(SizeProduct, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    quantity = models.IntegerField()

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    color = models.ForeignKey(ColorProduct, on_delete=models.CASCADE)
    size = models.ForeignKey(SizeProduct, on_delete=models.CASCADE)
    quantity = models.IntegerField()

class Order(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=255)
    shipping_type = models.CharField(max_length=255)
    is_company_order = models.BooleanField(default=False)
    additional_note = models.TextField(null=True, blank=True)
    total_price = models.DecimalField(max_digits=15, decimal_places=0)
    shipping_fee = models.DecimalField(max_digits=15, decimal_places=0)
    discounted_product = models.DecimalField(max_digits=15, decimal_places=0)
    discounted_shipping = models.DecimalField(max_digits=15, decimal_places=0)
    final_price = models.DecimalField(max_digits=15, decimal_places=0)
    created_at = models.DateTimeField(auto_now_add=True)

class AppliedVoucher(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE)
    class Meta:
        unique_together = ('user', 'voucher')  # Prevents duplicate use at DB level
