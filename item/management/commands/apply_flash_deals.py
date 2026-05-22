"""
Management command to automatically assign random flash discounts.

Selects 30-40% of all active (unsold) products and assigns a random
discount between 5% and 30% for a 48-hour window.

Scheduling
----------
Run every 48 hours via cron:

    0 0 */2 * * cd /path/to/project && python manage.py apply_flash_deals

Or on Windows Task Scheduler, create a task that runs every 2 days:

    Program:  C:\\path\\to\\python.exe
    Arguments: manage.py apply_flash_deals
    Start in: C:\\path\\to\\project

The command is idempotent — it clears all existing flash deals before
assigning new ones, so it can safely be re-run manually at any time.
"""

import math
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from item.models import item


class Command(BaseCommand):
    help = (
        "Clear existing flash deals and randomly assign discounts to "
        "30-40% of active (unsold) products for the next 48 hours."
    )

    def handle(self, *args, **options):
        now = timezone.now()
        end_time = now + timedelta(days=2)

        # ── Phase 1: Clear all existing flash discount assignments ──
        cleared_count = item.objects.filter(
            is_flash_discount_active=True
        ).count()

        item.objects.filter(is_flash_discount_active=True).update(
            is_flash_discount_active=False,
            flash_discount_percentage=0,
            flash_discount_start=None,
            flash_discount_end=None,
            discounted_price=None,
        )

        if cleared_count > 0:
            self.stdout.write(
                f"Cleared {cleared_count} previous flash discount assignment(s)."
            )

        # ── Phase 2: Get all active products ──
        active_ids = list(
            item.objects.filter(is_sold=False)
            .values_list('id', flat=True)
        )
        total = len(active_ids)

        if total == 0:
            self.stdout.write(
                self.style.WARNING("No active products found. Nothing to assign.")
            )
            return

        # ── Phase 3: Determine how many to select (30-40%) ──
        min_count = max(1, math.ceil(total * 0.30))
        max_count = min(total, math.floor(total * 0.40))

        # Tiny pool guard — make sure the floor isn't above the ceiling
        if min_count > max_count:
            min_count = max_count

        target_count = random.randint(min_count, max_count)

        self.stdout.write(
            f"Total active products: {total}. "
            f"Selecting {target_count} ({target_count / total * 100:.1f}%) "
            f"for flash discounts."
        )

        # ── Phase 4: Randomly select products (uniform distribution) ──
        selected_ids = random.sample(active_ids, target_count)

        # ── Phase 5: Assign discounts ──
        updated_items = []
        for pk in selected_ids:
            obj = item.objects.get(pk=pk)
            # Backfill original_price when it was never set
            if obj.original_price is None:
                obj.original_price = obj.price

            pct = random.randint(5, 30)
            discounted = round(float(obj.original_price) * (1 - pct / 100.0), 2)

            obj.flash_discount_percentage = pct
            obj.flash_discount_start = now
            obj.flash_discount_end = end_time
            obj.discounted_price = discounted
            obj.is_flash_discount_active = True

            updated_items.append(obj)

        # Bulk update for efficiency
        item.objects.bulk_update(
            updated_items,
            fields=[
                'original_price',
                'flash_discount_percentage',
                'flash_discount_start',
                'flash_discount_end',
                'discounted_price',
                'is_flash_discount_active',
            ],
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully assigned flash discounts to {target_count} products. "
                f"Discounts active from {now.strftime('%Y-%m-%d %H:%M UTC')} "
                f"until {end_time.strftime('%Y-%m-%d %H:%M UTC')}."
            )
        )

        # ── Summary stats ──
        discounts = [obj.flash_discount_percentage for obj in updated_items]
        avg_discount = sum(discounts) / len(discounts) if discounts else 0
        self.stdout.write(
            f"  Discount range: {min(discounts) if discounts else 0}% – "
            f"{max(discounts) if discounts else 0}% "
            f"(avg: {avg_discount:.1f}%)"
        )