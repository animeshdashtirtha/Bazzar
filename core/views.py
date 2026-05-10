from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from item.models import item
from django.template.loader import render_to_string
from core.models import Profile
from django.db.models import Q


def index(request):
    if request.user.is_authenticated:
        profile = getattr(request.user, 'core_profile', None)

        if profile and profile.user_type == 'seller':
            return redirect('core:my_items')

    q = request.GET.get('q', '').strip()
    limit = 10

    qs = item.objects.filter(is_sold=False)
    if q:
        # Searching by product name/description and category name
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(category__name__icontains=q)
        )

    qs = qs.order_by('-created_at')
    items = list(qs[:limit])
    has_more = qs.count() > limit

    return render(request, 'core/index.html', {'items': items, 'q': q, 'has_more': has_more})


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
        
       # Create Profile after user creation
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
        image = request.FILES.get('image')
        category = request.POST['category']

        new_item = item.objects.create(
            name=name,
            price=price,
            description=description,
            image=image,
            category_id=category,
            created_by=request.user
        )
        new_item.save()
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
    limit = 10
    q = request.GET.get('q', '').strip()

    qs = item.objects.filter(is_sold=False)
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(category__name__icontains=q)
        )

    qs = qs.order_by('-created_at')
    items = list(qs[offset:offset + limit])

    # Render HTML fragment using the same template as the grid cards
    html = render_to_string('core/item_card.html', {'items': items}, request=request)

    has_more = qs.count() > offset + limit

    return JsonResponse({'html': html, 'has_more': has_more, 'returned_count': len(items)})

