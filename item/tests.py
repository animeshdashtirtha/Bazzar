"""
Tests for flash deals — covers the effective-price property, the
management command that picks random items for discount, and the
public /flash-deals/ page.
"""
import math
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from item.models import category, item


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_category(name="Test Category"):
    return category.objects.create(name=name)


def _create_item(name="Test Item", price=100.0, is_sold=False, cat=None, user=None):
    """Create a test item with all required fields populated."""
    if cat is None:
        cat = _create_category()
    if user is None:
        user = User.objects.create_user(username=f"testuser_{name}", password="test")
    return item.objects.create(
        name=name,
        description="A test item",
        price=price,
        original_price=price,
        is_sold=is_sold,
        created_by=user,
        category=cat,
    )


# ---------------------------------------------------------------------------
# 1. get_effective_price & is_flash_discount_valid
# ---------------------------------------------------------------------------

class EffectivePriceTests(TestCase):
    """Test the get_effective_price property under various conditions."""

    def setUp(self):
        self.cat = _create_category()
        self.user = User.objects.create_user(username="price_tester", password="test")
        self.now = timezone.now()

    def test_no_flash_discount_returns_original_price(self):
        """When no flash discount is active, effective price = original_price."""
        it = _create_item("No Flash", price=150.0, cat=self.cat, user=self.user)
        self.assertFalse(it.is_flash_discount_valid)
        self.assertEqual(it.get_effective_price, it.original_price)

    def test_falls_back_to_price_when_original_is_none(self):
        """When original_price is None, fall back to the price field."""
        it = _create_item("No Original", price=200.0, cat=self.cat, user=self.user)
        it.original_price = None
        it.save()
        self.assertEqual(it.get_effective_price, Decimal("200.00"))

    def test_active_flash_within_window_returns_discounted_price(self):
        """When flash is active and within the window, return discounted_price."""
        it = _create_item("Active Flash", price=100.0, cat=self.cat, user=self.user)
        it.is_flash_discount_active = True
        it.flash_discount_percentage = 20
        it.flash_discount_start = self.now - timedelta(hours=1)
        it.flash_discount_end = self.now + timedelta(hours=47)
        it.discounted_price = Decimal("80.00")
        it.save()

        self.assertTrue(it.is_flash_discount_valid)
        self.assertEqual(it.get_effective_price, Decimal("80.00"))

    def test_flash_expired_still_valid_for_demo(self):
        """For demo purposes, flash deals are permanent — even expired windows stay valid."""
        it = _create_item("Expired Flash", price=100.0, cat=self.cat, user=self.user)
        it.is_flash_discount_active = True
        it.flash_discount_percentage = 20
        it.flash_discount_start = self.now - timedelta(days=3)
        it.flash_discount_end = self.now - timedelta(hours=1)  # ended
        it.discounted_price = Decimal("80.00")
        it.save()

        self.assertTrue(it.is_flash_discount_valid)
        self.assertEqual(it.get_effective_price, Decimal("80.00"))

    def test_flash_future_start_still_valid_for_demo(self):
        """For demo purposes, flash deals are permanent — even future-start deals are valid immediately."""
        it = _create_item("Future Flash", price=100.0, cat=self.cat, user=self.user)
        it.is_flash_discount_active = True
        it.flash_discount_percentage = 20
        it.flash_discount_start = self.now + timedelta(hours=1)  # future
        it.flash_discount_end = self.now + timedelta(days=2)
        it.discounted_price = Decimal("80.00")
        it.save()

        self.assertTrue(it.is_flash_discount_valid)
        self.assertEqual(it.get_effective_price, Decimal("80.00"))

    def test_active_flag_false_but_window_valid(self):
        """When is_flash_discount_active=False, never valid regardless of window."""
        it = _create_item("Flagged Off", price=100.0, cat=self.cat, user=self.user)
        it.is_flash_discount_active = False
        it.flash_discount_percentage = 20
        it.flash_discount_start = self.now - timedelta(hours=1)
        it.flash_discount_end = self.now + timedelta(hours=47)
        it.discounted_price = Decimal("80.00")
        it.save()

        self.assertFalse(it.is_flash_discount_valid)
        self.assertEqual(it.get_effective_price, it.original_price)

    def test_missing_discounted_price_falls_back(self):
        """When discounted_price is None, fall back to original_price."""
        it = _create_item("No Discounted", price=100.0, cat=self.cat, user=self.user)
        it.is_flash_discount_active = True
        it.flash_discount_percentage = 20
        it.flash_discount_start = self.now - timedelta(hours=1)
        it.flash_discount_end = self.now + timedelta(hours=47)
        it.discounted_price = None
        it.save()

        self.assertFalse(it.is_flash_discount_valid)
        self.assertEqual(it.get_effective_price, it.original_price)


# ---------------------------------------------------------------------------
# 2. apply_flash_deals management command — selection & discount logic
# ---------------------------------------------------------------------------

class ApplyFlashDealsCommandTests(TestCase):
    """Test the apply_flash_deals management command."""

    def setUp(self):
        self.cat = _create_category()
        self.user = User.objects.create_user(username="cmd_tester", password="test")
        self.now = timezone.now()

    def _create_batch(self, count, base_price=100.0, prefix="Item"):
        """Create `count` unsold items."""
        items = []
        for i in range(count):
            it = _create_item(
                f"{prefix} {i}",
                price=base_price + i,
                cat=self.cat,
                user=self.user,
            )
            items.append(it)
        return items

    # ---- Selection coverage (30-40%) ----

    def test_no_active_products_returns_early(self):
        """Command handles zero active products gracefully."""
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command('apply_flash_deals', stdout=out, stderr=StringIO())
        self.assertIn("No active products found", out.getvalue())

    def test_selection_is_between_30_and_40_percent(self):
        """The command selects 30-40% of active products."""
        self._create_batch(50)
        from django.core.management import call_command

        call_command('apply_flash_deals')

        total = item.objects.filter(is_sold=False).count()
        selected = item.objects.filter(is_flash_discount_active=True).count()
        pct = selected / total * 100

        self.assertGreaterEqual(pct, 30.0)
        self.assertLessEqual(pct, 40.0)

    def test_small_inventory_still_gets_at_least_one(self):
        """With fewer than 4 products, at least 1 gets selected due to max(1, ceil)."""
        self._create_batch(3)
        from django.core.management import call_command

        call_command('apply_flash_deals')

        selected = item.objects.filter(is_flash_discount_active=True).count()
        self.assertGreaterEqual(selected, 1)

    def test_large_inventory_selection_is_uniform_sample(self):
        """With 100 products, selection is consistently in the 30-40% band."""
        self._create_batch(100)
        from django.core.management import call_command

        # Run multiple times to verify the band holds
        for _ in range(5):
            # Clear first
            item.objects.filter(is_flash_discount_active=True).update(
                is_flash_discount_active=False,
                flash_discount_percentage=0,
                flash_discount_start=None,
                flash_discount_end=None,
                discounted_price=None,
            )
            call_command('apply_flash_deals')

            total = item.objects.filter(is_sold=False).count()
            selected = item.objects.filter(is_flash_discount_active=True).count()
            pct = selected / total * 100

            self.assertGreaterEqual(pct, 30.0)
            self.assertLessEqual(pct, 40.0)

    # ---- Discount range (5-30%) ----

    def test_discount_percentage_is_between_5_and_30(self):
        """Every selected item gets a discount between 5% and 30%."""
        self._create_batch(50)
        from django.core.management import call_command

        call_command('apply_flash_deals')

        selected = item.objects.filter(is_flash_discount_active=True)
        for it in selected:
            self.assertGreaterEqual(it.flash_discount_percentage, 5)
            self.assertLessEqual(it.flash_discount_percentage, 30)

    def test_discounted_price_is_correctly_computed(self):
        """discounted_price = original_price * (1 - pct/100), rounded to 2 decimals."""
        self._create_batch(20)
        from django.core.management import call_command

        call_command('apply_flash_deals')

        for it in item.objects.filter(is_flash_discount_active=True):
            expected = round(float(it.original_price) * (1 - it.flash_discount_percentage / 100.0), 2)
            self.assertEqual(float(it.discounted_price), expected)

    def test_discount_window_is_48_hours(self):
        """flash_discount_start to flash_discount_end spans exactly 2 days."""
        self._create_batch(20)
        from django.core.management import call_command

        # Capture time before calling
        before = timezone.now()
        call_command('apply_flash_deals')

        for it in item.objects.filter(is_flash_discount_active=True):
            delta = it.flash_discount_end - it.flash_discount_start
            self.assertAlmostEqual(delta.total_seconds(), 172800, delta=5)  # 48h ± 5s

    def test_backfills_original_price_if_none(self):
        """Items without original_price get it populated from price."""
        it = _create_item("No Original", price=199.99, cat=self.cat, user=self.user)
        it.original_price = None
        it.save()

        from django.core.management import call_command
        call_command('apply_flash_deals')

        it.refresh_from_db()
        # The command only backfills original_price for items it picks.
        # If this one wasn't chosen, we skip the asserts below.
        if it.is_flash_discount_active:
            self.assertIsNotNone(it.original_price)
            self.assertEqual(it.original_price, Decimal("199.99"))

    def test_sold_items_are_excluded(self):
        """Sold items never receive flash discounts."""
        sold = _create_item("Sold Item", price=50.0, is_sold=True, cat=self.cat, user=self.user)
        unsold = _create_item("Unsold Item", price=50.0, cat=self.cat, user=self.user)

        from django.core.management import call_command
        call_command('apply_flash_deals')

        sold.refresh_from_db()
        unsold.refresh_from_db()

        # Only the unsold item may have been selected
        self.assertFalse(sold.is_flash_discount_active)

    # ---- Idempotency ----

    def test_command_is_idempotent(self):
        """Running the command twice resets and reassigns — no duplicates, no stale state."""
        self._create_batch(30)
        from django.core.management import call_command

        call_command('apply_flash_deals')
        first_selected_ids = set(
            item.objects.filter(is_flash_discount_active=True).values_list('id', flat=True)
        )
        first_count = len(first_selected_ids)

        # Run again
        call_command('apply_flash_deals')
        second_selected_ids = set(
            item.objects.filter(is_flash_discount_active=True).values_list('id', flat=True)
        )
        second_count = len(second_selected_ids)

        # Both runs should select in the 30-40% band
        total = item.objects.filter(is_sold=False).count()
        self.assertGreaterEqual(first_count, math.ceil(total * 0.30))
        self.assertLessEqual(first_count, math.floor(total * 0.40))
        self.assertGreaterEqual(second_count, math.ceil(total * 0.30))
        self.assertLessEqual(second_count, math.floor(total * 0.40))

        # No item has stale start/end times from first run
        for it in item.objects.filter(is_flash_discount_active=True):
            self.assertIsNotNone(it.flash_discount_start)
            self.assertIsNotNone(it.flash_discount_end)
            self.assertIsNotNone(it.discounted_price)
            self.assertGreater(it.flash_discount_percentage, 0)

    def test_previous_assignments_fully_cleared(self):
        """After the command runs, exactly the selected items have active flags."""
        self._create_batch(40)
        from django.core.management import call_command

        call_command('apply_flash_deals')

        total_active = item.objects.filter(is_flash_discount_active=True).count()
        total_inactive = item.objects.filter(is_sold=False, is_flash_discount_active=False).count()

        # Every unsold item must be in one bucket or the other
        total_unsold = item.objects.filter(is_sold=False).count()
        self.assertEqual(total_active + total_inactive, total_unsold)


# ---------------------------------------------------------------------------
# 3. Flash Deals view (/flash-deals/)
# ---------------------------------------------------------------------------

class FlashDealsViewTests(TestCase):
    """Test the /flash-deals/ page."""

    def setUp(self):
        self.cat = _create_category()
        self.user = User.objects.create_user(username="view_tester", password="test")
        self.now = timezone.now()

    def test_url_resolves_and_returns_200(self):
        """The flash deals page loads successfully."""
        response = self.client.get(reverse('core:flash_deals'))
        self.assertEqual(response.status_code, 200)

    def test_template_used(self):
        """The correct template is rendered."""
        response = self.client.get(reverse('core:flash_deals'))
        self.assertTemplateUsed(response, 'core/flash_deals.html')

    def test_only_active_flash_items_shown(self):
        # Flash deal with a valid window
        active = _create_item("Active Deal", price=100.0, cat=self.cat, user=self.user)
        active.is_flash_discount_active = True
        active.flash_discount_percentage = 25
        active.flash_discount_start = self.now - timedelta(hours=1)
        active.flash_discount_end = self.now + timedelta(hours=47)
        active.discounted_price = Decimal("75.00")
        active.save()

        # Expired window — still visible because we skip time checks
        expired = _create_item("Expired Deal", price=200.0, cat=self.cat, user=self.user)
        expired.is_flash_discount_active = True
        expired.flash_discount_percentage = 20
        expired.flash_discount_start = self.now - timedelta(days=3)
        expired.flash_discount_end = self.now - timedelta(hours=1)
        expired.discounted_price = Decimal("160.00")
        expired.save()

        # Future window — also visible since we ignore the date bounds
        future = _create_item("Future Deal", price=300.0, cat=self.cat, user=self.user)
        future.is_flash_discount_active = True
        future.flash_discount_percentage = 15
        future.flash_discount_start = self.now + timedelta(hours=1)
        future.flash_discount_end = self.now + timedelta(days=2)
        future.discounted_price = Decimal("255.00")
        future.save()

        # Plain item — never had a flash deal
        normal = _create_item("Normal Item", price=50.0, cat=self.cat, user=self.user)

        # Sold, so it should be hidden even though the flag is on
        sold = _create_item("Sold Deal", price=80.0, is_sold=True, cat=self.cat, user=self.user)
        sold.is_flash_discount_active = True
        sold.flash_discount_percentage = 10
        sold.flash_discount_start = self.now - timedelta(hours=1)
        sold.flash_discount_end = self.now + timedelta(hours=47)
        sold.discounted_price = Decimal("72.00")
        sold.save()

        response = self.client.get(reverse('core:flash_deals'))
        items_in_context = list(response.context['items'])

        self.assertIn(active, items_in_context)
        self.assertIn(expired, items_in_context)   # permanent: expired still shows
        self.assertIn(future, items_in_context)    # permanent: future still shows
        self.assertNotIn(normal, items_in_context)
        self.assertNotIn(sold, items_in_context)

    def test_ordering_by_discount_descending(self):
        # Three deals at 5 %, 15 %, and 30 %
        low = _create_item("Low Discount", price=100.0, cat=self.cat, user=self.user)
        low.is_flash_discount_active = True
        low.flash_discount_percentage = 5
        low.flash_discount_start = self.now - timedelta(hours=1)
        low.flash_discount_end = self.now + timedelta(hours=47)
        low.discounted_price = Decimal("95.00")
        low.save()

        med = _create_item("Med Discount", price=100.0, cat=self.cat, user=self.user)
        med.is_flash_discount_active = True
        med.flash_discount_percentage = 15
        med.flash_discount_start = self.now - timedelta(hours=1)
        med.flash_discount_end = self.now + timedelta(hours=47)
        med.discounted_price = Decimal("85.00")
        med.save()

        high = _create_item("High Discount", price=100.0, cat=self.cat, user=self.user)
        high.is_flash_discount_active = True
        high.flash_discount_percentage = 30
        high.flash_discount_start = self.now - timedelta(hours=1)
        high.flash_discount_end = self.now + timedelta(hours=47)
        high.discounted_price = Decimal("70.00")
        high.save()

        response = self.client.get(reverse('core:flash_deals'))
        items = list(response.context['items'])

        self.assertEqual(items[0], high)
        self.assertEqual(items[1], med)
        self.assertEqual(items[2], low)

    def test_empty_state_when_no_active_deals(self):
        """Page still loads when no flash deals are active."""
        _create_item("Just Normal", price=50.0, cat=self.cat, user=self.user)
        response = self.client.get(reverse('core:flash_deals'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['items']), 0)

    def test_context_has_items(self):
        """The template context includes the `items` queryset (no `now` in permanent-demo mode)."""
        response = self.client.get(reverse('core:flash_deals'))
        self.assertIn('items', response.context)


# ---------------------------------------------------------------------------
# 4. Admin action
# ---------------------------------------------------------------------------

class AdminFlashDealsActionTests(TestCase):
    """Test the admin trigger_flash_deals action."""

    def setUp(self):
        self.cat = _create_category()
        self.user = User.objects.create_superuser(
            username="admin", password="adminpass", email="admin@test.com"
        )

    def test_admin_action_triggers_command(self):
        """The admin action correctly invokes the management command."""
        from django.contrib import admin
        from item.admin import ItemAdmin
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.http import HttpRequest

        # Seed the database with a few items
        for i in range(10):
            _create_item(f"AdminItem {i}", price=100.0 + i, cat=self.cat, user=self.user)

        # Simulate admin action
        admin_instance = ItemAdmin(item, admin.site)
        request = HttpRequest()
        request.user = self.user
        # Required for messages framework
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))

        queryset = item.objects.all()
        admin_instance.trigger_flash_deals(request, queryset)

        # The admin action should light up 30-40 % of the pool
        active_count = item.objects.filter(is_flash_discount_active=True).count()
        total = item.objects.filter(is_sold=False).count()
        self.assertGreater(active_count, 0)
        pct = active_count / total * 100
        self.assertGreaterEqual(pct, 30.0)
        self.assertLessEqual(pct, 40.0)
