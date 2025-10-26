from django.urls import path
from . import views

app_name = 'item'

urlpatterns = [
    path('<int:pk>/', views.detail, name='detail'),
    path('category/<int:pk>/', views.categories, name='categories')  ,
    path('edit-item/<int:pk>/', views.edit_item, name='edit_item'),
    path('delete-item/<int:pk>/', views.delete_item, name='delete_item'),
    path('seller/<int:seller_id>/', views.seller_items, name='seller_items'),
    ]