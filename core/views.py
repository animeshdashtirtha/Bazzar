from django.shortcuts import render
from item.models import item, category

def index(request):
    items = item.objects.filter(is_sold=False).order_by('-created_at')[0:6]
    categories = category.objects.all()
    context = {
        'items': items,
        'categoryies': categories}

    return render(request, 'core/index.html', context)

def contact(request):
    return render(request, 'core/contact.html')