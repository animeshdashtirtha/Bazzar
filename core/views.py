from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from item.models import item


def index(request):
    items = item.objects.filter(is_sold=False).order_by('-created_at')[:8]
    return render(request, 'core/index.html', {'items': items})

def about(request):
    return render(request, 'core/about.html')

def contact(request):
    return render(request, 'core/contact.html')

def policy(request):
    return render(request, 'core/policy.html')

def terms(request):
    return render(request, 'core/terms.html')


# ------------------ User Auth ------------------


def user_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        repeat_password = request.POST.get('repeatpassword')  # matches your template
        user_type = request.POST.get('user_type', 'buyer')  # default to 'buyer'

        # Password match check
        if password != repeat_password:
            messages.error(request, "Passwords do not match.")
            return redirect('core:signup')

        # Username/email uniqueness check
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('core:signup')
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect('core:signup')

        # Create user
        user = User.objects.create_user(username=username, email=email, password=password)
        
        # Save user_type if you have it in a profile model
        if hasattr(user, 'profile'):
            user.profile.user_type = user_type
            user.profile.save()

        # Log in the user
        login(request, user)
        messages.success(request, "Account created successfully!")
        if hasattr(user, 'core_profile') and user.core_profile.user_type == 'seller':
                return redirect('core:add_item')
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

            # Check user type if profile exists
            if hasattr(user, 'core_profile') and user.core_profile.user_type == 'seller':
                return redirect('core:add_item')
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


# ------------------ Seller item management ------------------

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
    user_items = item.objects.filter(created_by=request.user)
    return render(request, 'core/my_items.html', {'items': user_items})


# ------------------ AJAX pagination / lazy loading ------------------

def load_more_items(request):
    page = int(request.GET.get('page', 1))
    per_page = 8
    items_list = item.objects.filter(is_sold=False).order_by('-created_at')

    paginator = Paginator(items_list, per_page)
    try:
        items_page = paginator.page(page)
    except:
        return JsonResponse({'items': [], 'has_next': False})

    items_data = [
        {
            'id': i.id,
            'name': i.name,
            'price': str(i.price),
            'image': i.image.url if i.image else '',
            'category': i.category.name if i.category else '',
        }
        for i in items_page
    ]

    return JsonResponse({'items': items_data, 'has_next': items_page.has_next()})


