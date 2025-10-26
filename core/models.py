from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    USER_TYPES = (
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='core_profile')
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='buyer')

    def __str__(self):
        return f"{self.user.username} - {self.user_type}"