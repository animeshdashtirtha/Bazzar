from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import item, category


def detail(request, pk):
    item_obj = get_object_or_404(item, id=pk)
    related_items = item.objects.filter(category=item_obj.category, is_sold=False).exclude(id=item_obj.id).order_by("?")[:4]
    context = {
        'item': item_obj,
        'related_items': related_items,
    }
    return render(request, 'item/detail.html', context)


def categories(request, pk):
    from django.core.paginator import Paginator

    category_obj = get_object_or_404(category, id=pk)
    sort = request.GET.get('sort', 'random')
    page_num = request.GET.get('page', 1)
    limit = 12

    items_in_category = item.objects.filter(category=category_obj, is_sold=False)

    if sort == 'newest':
        items_in_category = items_in_category.order_by('-created_at')
    elif sort == 'price_asc':
        items_in_category = items_in_category.order_by('price')
    elif sort == 'price_desc':
        items_in_category = items_in_category.order_by('-price')
    else:
        items_in_category = items_in_category.order_by('?')

    paginator = Paginator(items_in_category, limit)
    page_obj = paginator.get_page(page_num)

    context = {
        'category': category_obj,
        'Categoryitems': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'sort': sort,
    }
    return render(request, 'item/categories.html', context)


# ---------------- File upload validation helpers ----------------

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB per file
ALLOWED_CONTENT_TYPES = ['image/jpeg', 'image/png', 'image/webp']
MAX_IMAGES_PER_ITEM = 5


def _validate_image_file(uploaded_file):
    """
    Validate a single uploaded image file.
    Returns (is_valid, error_message).
    """
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        return False, f"File '{uploaded_file.name}' exceeds the 5 MB size limit."
    if uploaded_file.content_type not in ALLOWED_CONTENT_TYPES:
        return False, f"File '{uploaded_file.name}' is not a supported image type (JPEG, PNG, or WebP only)."
    return True, None


# ----------------------------------------------------------------


@login_required
def edit_item(request, pk):
    item_obj = get_object_or_404(item, pk=pk, created_by=request.user)

    if request.method == 'POST':
        item_obj.name = request.POST.get('name')
        item_obj.description = request.POST.get('description')
        item_obj.price = request.POST.get('price')
        item_obj.category_id = request.POST.get('category')
        item_obj.save()

        from item.models import ItemImage

        keep_ids_raw = request.POST.getlist('existing_images')
        keep_ids = set()
        for raw_id in keep_ids_raw:
            try:
                keep_ids.add(int(raw_id))
            except (ValueError, TypeError):
                pass

        for img in item_obj.images.exclude(id__in=keep_ids):
            img.delete()

        for img_id in keep_ids:
            order_key = f'order_{img_id}'
            new_order = request.POST.get(order_key)
            if new_order is not None:
                try:
                    ItemImage.objects.filter(id=img_id, item=item_obj).update(
                        order=int(new_order)
                    )
                except (ValueError, TypeError):
                    pass

        new_images = request.FILES.getlist('new_images')
        existing_count = item_obj.images.count()
        total_after_add = existing_count + len(new_images)

        if total_after_add > MAX_IMAGES_PER_ITEM:
            messages.error(
                request,
                f'You can have at most {MAX_IMAGES_PER_ITEM} images per product. '
                f'You already have {existing_count} and tried to add {len(new_images)} more.'
            )
            categories = category.objects.all()
            return render(request, 'item/edit_item.html', {
                'item': item_obj,
                'categories': categories,
            })

        # Reject anything that isn't JPEG / PNG / WebP or is over 5 MB
        for img_file in new_images:
            is_valid, error_msg = _validate_image_file(img_file)
            if not is_valid:
                messages.error(request, error_msg)
                categories = category.objects.all()
                return render(request, 'item/edit_item.html', {
                    'item': item_obj,
                    'categories': categories,
                })

        next_order = item_obj.images.count()
        for idx, img_file in enumerate(new_images):
            ItemImage.objects.create(
                item=item_obj,
                image=img_file,
                order=next_order + idx,
            )

        messages.success(request, 'Item updated successfully!')
        return redirect('core:my_items')

    categories_queryset = category.objects.all()
    return render(request, 'item/edit_item.html', {
        'item': item_obj,
        'categories': categories_queryset,
    })


@login_required
def delete_item(request, pk):
    item_obj = get_object_or_404(item, pk=pk, created_by=request.user)

    if request.method == 'POST':
        item_obj.delete()
        messages.success(request, 'Item deleted successfully!')
        return redirect('core:my_items')

    return render(request, 'item/confirm_delete.html', {'item': item_obj})


def seller_items(request, seller_id):
    seller = get_object_or_404(User, id=seller_id)
    items = item.objects.filter(created_by=seller, is_sold=False).order_by('-created_at')

    context = {
        'seller': seller,
        'items': items,
    }
    return render(request, 'item/seller_items.html', context)
