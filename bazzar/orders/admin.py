from django.contrib import admin
from .models import Order, OrderItem

#  Custom action to confirm orders
def confirm_orders(modeladmin, request, queryset):
    for order in queryset:
        if order.status == 'pending':
            order.status = 'processing'
            order.save()  # triggers your post_save signal
confirm_orders.short_description = "Mark selected orders as confirmed"

#  Custom Order admin
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'id')
    readonly_fields = ('created_at',)
    list_editable = ('status',)  # allows inline editing in the list view
    actions = [confirm_orders]   # adds the bulk confirm action

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
