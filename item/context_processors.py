from django.core.cache import cache
from item.models import category


def categories_processor(request):
    categories = cache.get('all_categories')
    if categories is None:
        categories = list(category.objects.all())
        cache.set('all_categories', categories, 3600)  # 1 hour cache
    return {
        'categories': categories,
    }
