from django.contrib import admin
from .models import category, item, ItemImage


class ItemImageInline(admin.TabularInline):
    model = ItemImage
    extra = 1
    fields = ('image', 'order')
    ordering = ('order',)


class ItemAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'price', 'original_price', 'is_flash_discount_active',
        'flash_discount_percentage', 'discounted_price',
        'flash_discount_start', 'flash_discount_end', 'is_sold', 'created_at',
    )
    list_filter = ('is_flash_discount_active', 'is_sold', 'category')
    search_fields = ('name', 'description')
    readonly_fields = ('flash_discount_start', 'flash_discount_end')
    actions = ['trigger_flash_deals']
    inlines = [ItemImageInline]

    def trigger_flash_deals(self, request, queryset):
        """Admin action to manually trigger flash deal reassignment."""
        from django.core.management import call_command
        call_command('apply_flash_deals')
        self.message_user(request, "Flash deals have been reassigned successfully!")
    trigger_flash_deals.short_description = "🔄 Reassign Flash Deals"


admin.site.register(category)
admin.site.register(item, ItemAdmin)
