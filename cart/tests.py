from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from item.models import item, category
from cart.models import Cart, CartItem


class AddToCartTests(TestCase):
    """Test adding items to the cart via the add_to_cart and buy_now views."""

    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='testpass')
        self.cat = category.objects.create(name='Electronics')
        self.product = item.objects.create(
            name='Test Widget',
            price=99.99,
            description='A test widget',
            category=self.cat,
            created_by=self.user,
        )
        self.client.login(username='buyer', password='testpass')

    def test_add_to_cart_creates_cart_and_cart_item(self):
        """Adding an item should create a Cart and CartItem if they don't exist."""
        url = reverse('cart:add_to_cart', args=[self.product.id])
        self.client.get(url)

        cart = Cart.objects.get(user=self.user)
        self.assertIsNotNone(cart)
        cart_item = CartItem.objects.get(cart=cart, item=self.product)
        self.assertEqual(cart_item.quantity, 1)

    def test_add_same_item_increments_quantity(self):
        """Adding the same item again should increment quantity."""
        url = reverse('cart:add_to_cart', args=[self.product.id])
        self.client.get(url)  # first time
        self.client.get(url)  # second time

        cart = Cart.objects.get(user=self.user)
        cart_item = CartItem.objects.get(cart=cart, item=self.product)
        self.assertEqual(cart_item.quantity, 2)

    def test_add_to_cart_with_custom_quantity(self):
        """Providing ?quantity=N should set that quantity on first add."""
        url = reverse('cart:add_to_cart', args=[self.product.id]) + '?quantity=5'
        self.client.get(url)

        cart_item = CartItem.objects.get(cart__user=self.user, item=self.product)
        self.assertEqual(cart_item.quantity, 5)

    def test_add_to_cart_invalid_quantity_defaults_to_one(self):
        """Non-integer quantity values should default to 1."""
        url = reverse('cart:add_to_cart', args=[self.product.id]) + '?quantity=abc'
        self.client.get(url)

        cart_item = CartItem.objects.get(cart__user=self.user, item=self.product)
        self.assertEqual(cart_item.quantity, 1)

    def test_add_to_cart_quantity_clamped_maximum(self):
        """Quantity should be clamped to a maximum of 99."""
        url = reverse('cart:add_to_cart', args=[self.product.id]) + '?quantity=150'
        self.client.get(url)

        cart_item = CartItem.objects.get(cart__user=self.user, item=self.product)
        self.assertEqual(cart_item.quantity, 99)

    def test_add_to_cart_quantity_clamped_minimum(self):
        """Quantity should be clamped to a minimum of 1."""
        url = reverse('cart:add_to_cart', args=[self.product.id]) + '?quantity=-5'
        self.client.get(url)

        cart_item = CartItem.objects.get(cart__user=self.user, item=self.product)
        self.assertEqual(cart_item.quantity, 1)

    def test_add_to_cart_nonexistent_item_returns_404(self):
        """Adding a non-existent item ID should return a 404."""
        url = reverse('cart:add_to_cart', args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_buy_now_redirects_to_checkout(self):
        """buy_now should redirect to the checkout page."""
        url = reverse('cart:buy_now', args=[self.product.id])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('cart:checkout'))

    def test_add_to_cart_requires_login(self):
        """Unauthenticated users should be redirected to login."""
        self.client.logout()
        url = reverse('cart:add_to_cart', args=[self.product.id])
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('login', response.url)


class ViewCartTests(TestCase):
    """Test the cart viewing page."""

    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='testpass')
        self.cat = category.objects.create(name='Books')
        self.product = item.objects.create(
            name='Django Book',
            price=29.99,
            description='Learn Django',
            category=self.cat,
            created_by=self.user,
        )
        self.client.login(username='buyer', password='testpass')

    def test_view_empty_cart(self):
        """Viewing an empty cart should still render the page."""
        response = self.client.get(reverse('cart:view_cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'cart is empty')

    def test_view_cart_with_items(self):
        """Cart with items should show product details."""
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, item=self.product, quantity=2)

        response = self.client.get(reverse('cart:view_cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django Book')

    def test_cart_total_with_multiple_items(self):
        """Cart total should sum item totals correctly."""
        cart, _ = Cart.objects.get_or_create(user=self.user)
        product2 = item.objects.create(
            name='Python Book', price=19.99,
            category=self.cat, created_by=self.user,
        )
        CartItem.objects.create(cart=cart, item=self.product, quantity=2)
        CartItem.objects.create(cart=cart, item=product2, quantity=1)

        # 29.99 * 2 + 19.99 * 1 ≈ 79.97
        expected_total = 29.99 * 2 + 19.99 * 1
        self.assertAlmostEqual(cart.total_price(), expected_total, places=2)


class RemoveFromCartTests(TestCase):
    """Test removing items from the cart."""

    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='testpass')
        self.cat = category.objects.create(name='Home')
        self.product = item.objects.create(
            name='Lamp', price=15.00,
            category=self.cat, created_by=self.user,
        )
        self.client.login(username='buyer', password='testpass')

    def test_remove_item_from_cart(self):
        """Removing an item should delete the CartItem."""
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, item=self.product, quantity=1)

        url = reverse('cart:remove_from_cart', args=[self.product.id])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('cart:view_cart'))

        self.assertFalse(CartItem.objects.filter(cart=cart, item=self.product).exists())

    def test_remove_nonexistent_item_returns_404(self):
        """Removing an item not in the cart should return 404."""
        url = reverse('cart:remove_from_cart', args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class UpdateQuantityTests(TestCase):
    """Test updating cart item quantities."""

    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='testpass')
        self.cat = category.objects.create(name='Clothing')
        self.product = item.objects.create(
            name='T-Shirt', price=25.00,
            category=self.cat, created_by=self.user,
        )
        self.client.login(username='buyer', password='testpass')

    def test_increase_quantity(self):
        """Increasing quantity should add 1."""
        cart, _ = Cart.objects.get_or_create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, item=self.product, quantity=2)

        url = reverse('cart:update_quantity', args=[self.product.id])
        self.client.post(url, {'action': 'increase'})

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)

    def test_decrease_quantity(self):
        """Decreasing quantity should subtract 1."""
        cart, _ = Cart.objects.get_or_create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, item=self.product, quantity=3)

        url = reverse('cart:update_quantity', args=[self.product.id])
        self.client.post(url, {'action': 'decrease'})

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)

    def test_decrease_at_one_does_nothing(self):
        """Decreasing quantity when already at 1 should not go below 1."""
        cart, _ = Cart.objects.get_or_create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, item=self.product, quantity=1)

        url = reverse('cart:update_quantity', args=[self.product.id])
        self.client.post(url, {'action': 'decrease'})

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 1)


class CartModelTests(TestCase):
    """Test Cart and CartItem model methods."""

    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='testpass')
        self.cat = category.objects.create(name='Gadgets')
        self.product = item.objects.create(
            name='Mouse', price=50.00,
            category=self.cat, created_by=self.user,
        )

    def test_cart_str(self):
        cart = Cart.objects.create(user=self.user)
        self.assertIn('buyer', str(cart))

    def test_cart_item_str(self):
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, item=self.product, quantity=3)
        self.assertIn('Mouse', str(cart_item))
        self.assertIn('3', str(cart_item))

    def test_cart_item_total(self):
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, item=self.product, quantity=3)
        self.assertEqual(cart_item.total(), 50.00 * 3)

    def test_cart_item_total_with_flash_discount(self):
        """Cart total should use get_effective_price (flash discount aware)."""
        self.product.original_price = self.product.price
        self.product.is_flash_discount_active = True
        self.product.flash_discount_percentage = 20
        self.product.discounted_price = 40.00  # 20% off 50
        self.product.save()

        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, item=self.product, quantity=2)

        # Should use discounted price: 40.00 * 2 = 80.00
        self.assertEqual(cart_item.total(), 80.00)
