from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.utils import timezone
from item.models import item
from django.template.loader import render_to_string
from core.models import Profile
from django.db.models import Q
from django_ratelimit.decorators import ratelimit

# ---------------------------------------------------------------------------
# Shared helper utilities
# ---------------------------------------------------------------------------

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB per file
ALLOWED_CONTENT_TYPES = ['image/jpeg', 'image/png', 'image/webp']
MAX_IMAGES_PER_ITEM = 5


def _validate_image_file(uploaded_file):
    """Return (is_valid, error_message) for a single uploaded image."""
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        return False, f"File '{uploaded_file.name}' exceeds the 5 MB size limit."
    if uploaded_file.content_type not in ALLOWED_CONTENT_TYPES:
        return False, f"File '{uploaded_file.name}' is not a supported image type (JPEG, PNG, or WebP only)."
    return True, None


def _clear_random_session(request):
    """Remove session-stored random ordering so deterministic sorts take over."""
    for key in ('random_item_order', 'random_item_query'):
        try:
            del request.session[key]
        except KeyError:
            pass
    request.session.modified = True


def _apply_search_filter(qs, q):
    """Apply the shared name/description/category search filter to a queryset."""
    if not q:
        return qs
    return qs.filter(
        Q(name__icontains=q)
        | Q(description__icontains=q)
        | Q(category__name__icontains=q)
    )


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


def index(request):
    if request.user.is_authenticated:
        profile = getattr(request.user, 'core_profile', None)

        if profile and profile.user_type == 'seller':
            return redirect('core:my_items')

    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'random')
    page_num = request.GET.get('page', 1)
    limit = 12

    # Base queryset with shared search filter
    base_qs = _apply_search_filter(item.objects.filter(is_sold=False), q)

    if sort == 'newest':
        _clear_random_session(request)
        qs = base_qs.order_by('-created_at')
        paginator = Paginator(qs, limit)
        page_obj = paginator.get_page(page_num)
        items = page_obj.object_list

    elif sort == 'price_asc':
        _clear_random_session(request)
        qs = base_qs.order_by('price')
        paginator = Paginator(qs, limit)
        page_obj = paginator.get_page(page_num)
        items = page_obj.object_list

    elif sort == 'price_desc':
        _clear_random_session(request)
        qs = base_qs.order_by('-price')
        paginator = Paginator(qs, limit)
        page_obj = paginator.get_page(page_num)
        items = page_obj.object_list

    else:
        # Stash a shuffled id list in the session — pagination walks
        # through it page by page so the order stays fixed.
        session_key = 'random_item_order'
        session_q_key = 'random_item_query'

        stored_ids = request.session.get(session_key)
        stored_q = request.session.get(session_q_key, '')

        # Re-shuffle when the session order is missing or the user changed
        # their search term
        if not stored_ids or stored_q != q:
            ids = list(base_qs.order_by('?').values_list('id', flat=True))
            request.session[session_key] = ids
            request.session[session_q_key] = q
            request.session.modified = True
            stored_ids = ids

        # Paginate over the id list to get stable pages
        paginator = Paginator(stored_ids, limit)
        page_obj = paginator.get_page(page_num)
        page_ids = list(page_obj.object_list)

        # Pull the actual model instances for the current slice,
        # then sort them back into the session's shuffled order.
        items_qs = item.objects.filter(id__in=page_ids)
        items = sorted(items_qs, key=lambda x: page_ids.index(x.id))

    return render(request, 'core/index.html', {
        'items': items,
        'q': q,
        'page_obj': page_obj,
        'paginator': paginator,
        'sort': sort
    })


def about(request):
    return render(request, 'core/about.html')

def contact(request):
    return render(request, 'core/contact.html')

def policy(request):
    return render(request, 'core/policy.html')

def terms(request):
    return render(request, 'core/terms.html')

def inbox(request):
    return render(request, 'core/inbox.html')

@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def user_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        repeat_password = request.POST.get('repeatpassword')  # matches your template
        user_type = request.POST.get('user_type', 'buyer')  # default to 'buyer'

        if password != repeat_password:
            messages.error(request, "Passwords do not match.")
            return redirect('core:signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('core:signup')
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect('core:signup')

        user = User.objects.create_user(username=username, email=email, password=password)
        
        # Attach a profile row to the new user
        Profile.objects.update_or_create(
            user=user,
            defaults={'user_type': user_type}
        )
        user.refresh_from_db() 

        login(request, user)
        messages.success(request, "Account created successfully!")
        if hasattr(user, 'core_profile') and user.core_profile.user_type == 'seller':
                return redirect('core:my_items')
        else:
            return redirect('core:index')

    return render(request, 'core/signup.html')


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if hasattr(user, 'core_profile') and user.core_profile.user_type == 'seller':
                return redirect('core:my_items')
            else:
                return redirect('core:index')
        
        else:
            messages.error(request, 'Invalid username or password.')
            return redirect('core:login')

    return render(request, 'core/login.html')



@login_required
def user_logout(request):
    logout(request)
    return redirect('core:index')


@login_required
def add_item(request):
    if request.method == 'POST':
        name = request.POST['name']
        price = request.POST['price']
        description = request.POST['description']
        category_id = request.POST['category']

        # Collect every file sent through the multi-image input
        uploaded_images = request.FILES.getlist('images')

        # Server-side validation: at most 5 images
        if len(uploaded_images) > MAX_IMAGES_PER_ITEM:
            messages.error(request, f'You can upload at most {MAX_IMAGES_PER_ITEM} images per product.')
            return render(request, 'core/add_item.html')

        # Reject anything that isn't JPEG / PNG / WebP or is over 5 MB
        for img_file in uploaded_images:
            is_valid, err_msg = _validate_image_file(img_file)
            if not is_valid:
                messages.error(request, err_msg)
                return render(request, 'core/add_item.html')

        new_item = item.objects.create(
            name=name,
            price=price,
            description=description,
            category_id=category_id,
            created_by=request.user
        )

        # Persist each accepted image, keeping the upload sequence
        for idx, img_file in enumerate(uploaded_images):
            from item.models import ItemImage
            ItemImage.objects.create(
                item=new_item,
                image=img_file,
                order=idx,
            )

        messages.success(request, 'Item added successfully!')
        return redirect('core:my_items')

    return render(request, 'core/add_item.html')


@login_required
def my_items(request):
    user_items = item.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'core/my_items.html', {'items': user_items})


# ------------------ AJAX pagination / lazy loading ------------------

def load_more_items(request):
    offset = int(request.GET.get('offset', 0))
    limit = 12
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'random')

    if sort == 'newest':
        # Newest first - no session needed
        qs = _apply_search_filter(item.objects.filter(is_sold=False), q)
        total_count = qs.count()
        items = list(qs.order_by('-created_at')[offset:offset + limit])
        has_more = total_count > offset + limit

    elif sort == 'price_asc':
        qs = _apply_search_filter(item.objects.filter(is_sold=False), q)
        total_count = qs.count()
        items = list(qs.order_by('price')[offset:offset + limit])
        has_more = total_count > offset + limit

    elif sort == 'price_desc':
        qs = _apply_search_filter(item.objects.filter(is_sold=False), q)
        total_count = qs.count()
        items = list(qs.order_by('-price')[offset:offset + limit])
        has_more = total_count > offset + limit

    else:
        # Reuse the session-stored shuffle so "load more" continues
        # the same random order the user already sees on the page.
        session_key = 'random_item_order'
        session_q_key = 'random_item_query'

        # If session order is missing or search query changed, (re)generate it
        stored_ids = request.session.get(session_key)
        stored_q = request.session.get(session_q_key, '')

        if not stored_ids or stored_q != q:
            qs = _apply_search_filter(item.objects.filter(is_sold=False), q)
            stored_ids = list(qs.order_by('?').values_list('id', flat=True))
            request.session[session_key] = stored_ids
            request.session[session_q_key] = q
            request.session.modified = True

        item_ids = stored_ids

        total_count = len(item_ids)
        page_item_ids = item_ids[offset:offset + limit]
        items = list(item.objects.filter(id__in=page_item_ids))
        items = sorted(items, key=lambda x: item_ids.index(x.id))
        has_more = total_count > offset + limit

    # Return just the card grid as HTML — the front-end appends it.
    html = render_to_string('core/item_card.html', {'items': items}, request=request)

    return JsonResponse({'html': html, 'has_more': has_more, 'returned_count': len(items)})


def flash_deals(request):
    flash_items = item.objects.filter(
        is_flash_discount_active=True,
        is_sold=False,
    ).order_by('-flash_discount_percentage')

    return render(request, 'core/flash_deals.html', {
        'items': flash_items,
    })
