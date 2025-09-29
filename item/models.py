from django.db import models
from django.contrib.auth.models import User
# Create your models here.
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
    image=models.ImageField(upload_to='item_images', blank=False, null=False)

    def __str__(self):
        return self.name

