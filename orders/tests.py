from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from item.models import item, category
from cart.models import Cart, CartItem
from orders.models import Order, OrderItem


class OrderCreationTests(TestCase):
    """Test order creation through the checkout flow."""

    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='testpass')
        self.cat = category.objects.create(name='Electronics')
        self.product = item.objects.create(
            name='Test Widget',
            price=100.00,
            description='A test widget',
            category=self.cat,
            created_by=self.user,
        )
        self.client.login(username='buyer', password='testpass')

    def test_checkout_creates_order_and_order_items(self):
        """Submitting checkout with items should create Order + OrderItems."""
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, item=self.product, quantity=2)

        response = self.client.post(reverse('cart:checkout'))

        self.assertRedirects(response, reverse('orders:my_orders'))

        order = Order.objects.get(user=self.user)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.items.count(), 1)

        order_item = order.items.first()
        self.assertEqual(order_item.item, self.product)
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(float(order_item.price), 100.00)

    def test_checkout_clears_cart_after_order(self):
        """Cart items should be deleted after a successful order."""
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, item=self.product, quantity=1)

        self.client.post(reverse('cart:checkout'))

        self.assertFalse(CartItem.objects.filter(cart=cart).exists())

    def test_checkout_with_empty_cart_redirects(self):
        """Checkout with an empty cart should redirect back to cart view."""
        response = self.client.post(reverse('cart:checkout'))
        self.assertRedirects(response, reverse('cart:view_cart'))

    def test_checkout_price_uses_effective_price(self):
        """Order should use get_effective_price (with flash discount) not raw price."""
        self.product.original_price = self.product.price
        self.product.is_flash_discount_active = True
        self.product.flash_discount_percentage = 20
        self.product.discounted_price = 80.00
        self.product.save()

        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, item=self.product, quantity=1)

        response = self.client.post(reverse('cart:checkout'))
        self.assertEqual(response.status_code, 302)

        order = Order.objects.get(user=self.user)
        order_item = order.items.first()
        self.assertEqual(float(order_item.price), 80.00)

    def test_checkout_total_price_matches_items(self):
        """Order.total_price should equal sum of all OrderItem totals."""
        product2 = item.objects.create(
            name='Second Widget', price=50.00,
            category=self.cat, created_by=self.user,
        )

        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, item=self.product, quantity=2)
        CartItem.objects.create(cart=cart, item=product2, quantity=3)

        self.client.post(reverse('cart:checkout'))

        order = Order.objects.get(user=self.user)
        # 100 * 2 + 50 * 3 = 350.00
        self.assertEqual(float(order.total_price), 350.00)


class MyOrdersViewTests(TestCase):
    """Test the my_orders listing page."""

    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='testpass')
        self.cat = category.objects.create(name='Books')
        self.product = item.objects.create(
            name='Django Book', price=49.99,
            category=self.cat, created_by=self.user,
        )
        self.client.login(username='buyer', password='testpass')

    def test_my_orders_empty(self):
        """The my_orders page should render for a user with no orders."""
        response = self.client.get(reverse('orders:my_orders'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No orders')

    def test_my_orders_shows_existing_order(self):
        """Orders belonging to the user should appear on the page."""
        order = Order.objects.create(user=self.user, total_price=99.98)
        OrderItem.objects.create(order=order, item=self.product, quantity=2, price=49.99)

        response = self.client.get(reverse('orders:my_orders'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django Book')

    def test_my_orders_only_shows_user_orders(self):
        """A user should only see their own orders."""
        other_user = User.objects.create_user(username='other', password='testpass')
        Order.objects.create(user=other_user, total_price=50.00)

        response = self.client.get(reverse('orders:my_orders'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No orders')

    def test_my_orders_requires_login(self):
        """Unauthenticated users should be redirected."""
        self.client.logout()
        response = self.client.get(reverse('orders:my_orders'))
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('login', response.url)


class OrderModelTests(TestCase):
    """Test the Order and OrderItem model methods."""

    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='testpass')
        self.cat = category.objects.create(name='Gadgets')
        self.product = item.objects.create(
            name='Keyboard', price=80.00,
            category=self.cat, created_by=self.user,
        )

    def test_order_str(self):
        order = Order.objects.create(user=self.user, total_price=160.00)
        self.assertIn(str(order.id), str(order))
        self.assertIn('buyer', str(order))

    def test_order_item_str(self):
        order = Order.objects.create(user=self.user, total_price=80.00)
        order_item = OrderItem.objects.create(
            order=order, item=self.product, quantity=1, price=80.00
        )
        self.assertIn('Keyboard', str(order_item))

    def test_order_default_status_is_pending(self):
        """New orders should default to 'pending' status."""
        order = Order.objects.create(user=self.user, total_price=100.00)
        self.assertEqual(order.status, 'pending')

    def test_order_status_choices_valid(self):
        """Setting status to each valid choice should work."""
        order = Order.objects.create(user=self.user, total_price=100.00)
        for status in ['pending', 'processing', 'shipped', 'delivered', 'cancelled']:
            order.status = status
            order.save()
            order.refresh_from_db()
            self.assertEqual(order.status, status)
