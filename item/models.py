from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from slugify import slugify


class category(models.Model):
    name = models.CharField(max_length=225)
    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name',]

    def __str__(self):
        return self.name
    

class item(models.Model):
    name = models.CharField(max_length=225)
    description=models.TextField(blank=True, null=True)
    price=models.FloatField()
    is_sold=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    created_by=models.ForeignKey(User, related_name='items', on_delete=models.CASCADE)
    category=models.ForeignKey(category,related_name='items', on_delete=models.CASCADE)

    # ---- Flash Discount fields ----
    original_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Price before any flash discount was applied"
    )
    is_flash_discount_active = models.BooleanField(
        default=False,
        help_text="Ticked when this product is part of the current flash batch"
    )
    flash_discount_percentage = models.PositiveSmallIntegerField(
        default=0,
        help_text="Discount percent applied (5–30)"
    )
    flash_discount_start = models.DateTimeField(null=True, blank=True)
    flash_discount_end = models.DateTimeField(null=True, blank=True)
    discounted_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="original_price minus the flash discount, rounded to 2 decimals"
    )

    def __str__(self):
        return self.name

    @property
    def primary_image(self):
        """First image in gallery order — the one shown on cards."""
        first = self.images.first()
        return first.image if first else None

    @property
    def get_effective_price(self):
        """Price the buyer actually pays: discounted_price if there's an active
        flash deal, otherwise original_price, falling back to the raw price field.

        Flash deals are permanent in this build — we skip time-window checks so
        items stay discounted until the admin re-rolls the batch."""
        if (self.is_flash_discount_active
                and self.discounted_price is not None):
            return self.discounted_price
        if self.original_price is not None:
            return self.original_price
        return self.price

    @property
    def is_flash_discount_valid(self):
        """True when the flash flag is on *and* a discounted price was computed.
        No time-window gating — deals stick until the next manual refresh."""
        return (
            self.is_flash_discount_active
            and self.discounted_price is not None
        )


class ItemImage(models.Model):
    """One image in an item's gallery — sortable via the ``order`` field."""
    item = models.ForeignKey(item, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='item_images')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Item Image"
        verbose_name_plural = "Item Images"

    def __str__(self):
        return f"Image {self.order} for {self.item.name}"

    def delete(self, *args, **kwargs):
        """Nuke the file on disk before removing the db row."""
        if self.image:
            storage = self.image.storage
            name = self.image.name
            if storage.exists(name):
                storage.delete(name)
        super().delete(*args, **kwargs)


class Profile(models.Model):
    USER_ROLES = (
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=USER_ROLES, default='buyer')

    def __str__(self):
        return f"{self.user.username} ({self.role})"
