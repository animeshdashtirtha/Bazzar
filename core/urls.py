from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('contact/', views.contact, name='contact'), 
    path('policy/', views.policy, name='policy'), 
    path('terms/', views.terms, name='terms'), 
    path('about/', views.about, name='about'),
    path('signup/', views.user_signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout')  ,
    path('add-item/', views.add_item, name='add_item'),
    path('my-items/', views.my_items, name='my_items'),
    path('load-more-items/', views.load_more_items, name='load_more_items'),
]