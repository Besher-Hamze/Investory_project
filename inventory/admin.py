from django.contrib import admin

from .models import Notification, Product, StockLevel, StockMovement, Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_main', 'is_active', 'total_quantity')
    list_filter = ('is_main', 'is_active')
    search_fields = ('name', 'code')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'barcode', 'price', 'min_quantity', 'total_quantity', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'sku', 'barcode')


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity', 'entry_date', 'effective_date', 'expiry_date', 'updated_at')
    list_filter = ('warehouse',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'product', 'movement_type', 'quantity', 'entry_date', 'expiry_date', 'user')
    list_filter = ('movement_type', 'created_at')
    search_fields = ('product__name', 'reference_number')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
