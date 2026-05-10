from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('my-orders/', views.my_orders, name='my_orders'),
]
