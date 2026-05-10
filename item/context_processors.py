from item.models import category, item

def categories_processor(request):
    return {
        'categories': category.objects.all(),
        'items': item.objects.all()
    }
