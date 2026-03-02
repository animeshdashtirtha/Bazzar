from django.db import models
from django.contrib.auth.models import User
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
    image=models.ImageField(upload_to='item_images', blank=True, null=True)

    def __str__(self):
        return self.name


class Profile(models.Model):
    USER_ROLES = (
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=USER_ROLES, default='buyer')

    def __str__(self):
        return f"{self.user.username} ({self.role})"


