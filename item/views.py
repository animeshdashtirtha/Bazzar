from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import item, category


def detail(request, pk):
    item_obj = item.objects.get(id=pk)
    related_items = item.objects.filter(category=item_obj.category, is_sold=False).exclude(id=item_obj.id).order_by("?")[:4]
    context = {
        'item': item_obj,
        'related_items': related_items,
    }
    return render(request, 'item/detail.html', context)

def categories(request, pk):
    category_obj = category.objects.get(id=pk)
    items_in_category = item.objects.filter(category=category_obj, is_sold=False).order_by('-created_at')
    context = {
        'category': category_obj,
        'Categoryitems': items_in_category,
    }
    return render(request, 'item/categories.html', context)


# Edit Item
@login_required
def edit_item(request, pk):
    item_obj = get_object_or_404(item, pk=pk, created_by=request.user)

    if request.method == 'POST':
        item_obj.name = request.POST.get('name')
        item_obj.description = request.POST.get('description')
        item_obj.price = request.POST.get('price')
        item_obj.category_id = request.POST.get('category')

        if request.FILES.get('image'):
            item_obj.image = request.FILES['image']

        item_obj.save()
        messages.success(request, 'Item updated successfully!')
        return redirect('core:my_items')

    categories = category.objects.all()
    return render(request, 'item/edit_item.html', {
        'item': item_obj,
        'categories': categories,
    })


# Delete Item
@login_required
def delete_item(request, pk):
    item_obj = get_object_or_404(item, pk=pk, created_by=request.user)

    if request.method == 'POST':
        item_obj.delete()
        messages.success(request, 'Item deleted successfully!')
        return redirect('core:my_items')

    return render(request, 'item/confirm_delete.html', {'item': item_obj})



# seller_items_page
def seller_items(request, seller_id):
    seller = get_object_or_404(User, id=seller_id)
    items = item.objects.filter(created_by=seller, is_sold=False).order_by('-created_at')
    
    context = {
        'seller': seller,
        'items': items,
    }
    return render(request, 'item/seller_items.html', context)


