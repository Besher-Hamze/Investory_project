import uuid

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Warehouse(models.Model):
    name = models.CharField('اسم المستودع', max_length=200)
    code = models.CharField('رمز المستودع', max_length=20, unique=True)
    address = models.TextField('العنوان', blank=True)
    is_main = models.BooleanField('مستودع رئيسي', default=False)
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'مستودع'
        verbose_name_plural = 'المستودعات'
        ordering = ['-is_main', 'name']

    def __str__(self):
        return self.name

    @property
    def total_quantity(self):
        return self.stock_levels.aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def total_value(self):
        total = self.stock_levels.select_related('product').aggregate(
            value=Sum(models.F('quantity') * models.F('product__price'))
        )['value']
        return total or 0


class Product(models.Model):
    name = models.CharField('اسم المنتج', max_length=200)
    sku = models.CharField('SKU', max_length=50, unique=True)
    barcode = models.CharField('الباركود', max_length=100, unique=True, blank=True)
    price = models.DecimalField('السعر', max_digits=12, decimal_places=2)
    min_quantity = models.PositiveIntegerField('الحد الأدنى', default=0)
    shelf = models.CharField('الرف', max_length=50, blank=True)
    rack_number = models.CharField('رقم الموقع', max_length=50, blank=True)
    description = models.TextField('الوصف', blank=True)
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'منتج'
        verbose_name_plural = 'المنتجات'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.sku})'

    def save(self, *args, **kwargs):
        if not self.barcode:
            self.barcode = self.sku.replace('-', '').upper()[:20] or uuid.uuid4().hex[:12].upper()
        super().save(*args, **kwargs)

    @property
    def total_quantity(self):
        return self.stock_levels.aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def is_low_stock(self):
        return self.total_quantity <= self.min_quantity

    @property
    def location_display(self):
        parts = [p for p in [self.shelf, self.rack_number] if p]
        return ' - '.join(parts) if parts else '—'


class StockLevel(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_levels', verbose_name='المنتج')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_levels', verbose_name='المستودع')
    quantity = models.PositiveIntegerField('الكمية', default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'مخزون'
        verbose_name_plural = 'المخزون'
        unique_together = ('product', 'warehouse')

    def __str__(self):
        return f'{self.product.name} @ {self.warehouse.name}: {self.quantity}'


class MovementType(models.TextChoices):
    IN_PURCHASE = 'in_purchase', 'فاتورة شراء'
    IN_RECEIPT = 'in_receipt', 'أمر استلام'
    OUT_SALE = 'out_sale', 'فاتورة بيع'
    OUT_DISPATCH = 'out_dispatch', 'أمر صرف'
    TRANSFER = 'transfer', 'نقل بين مستودعات'


class StockMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements', verbose_name='المنتج')
    movement_type = models.CharField('نوع العملية', max_length=20, choices=MovementType.choices)
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name='movements',
        verbose_name='المستودع', null=True, blank=True,
    )
    warehouse_from = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name='transfers_out',
        verbose_name='من مستودع', null=True, blank=True,
    )
    warehouse_to = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name='transfers_in',
        verbose_name='إلى مستودع', null=True, blank=True,
    )
    quantity = models.PositiveIntegerField('الكمية')
    quantity_before = models.PositiveIntegerField('الكمية قبل')
    quantity_after = models.PositiveIntegerField('الكمية بعد')
    reference_number = models.CharField('رقم المرجع', max_length=100, blank=True)
    notes = models.TextField('ملاحظات', blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='stock_movements', verbose_name='المستخدم')
    created_at = models.DateTimeField('التاريخ', default=timezone.now)

    class Meta:
        verbose_name = 'حركة مخزون'
        verbose_name_plural = 'سجل الحركة'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_movement_type_display()} - {self.product.name}'

    @property
    def movement_label(self):
        if self.movement_type == MovementType.TRANSFER:
            return f'نقل: {self.warehouse_from} → {self.warehouse_to}'
        return self.get_movement_type_display()


class NotificationType(models.TextChoices):
    LOW_STOCK = 'low_stock', 'مخزون منخفض'
    SYSTEM = 'system', 'نظام'


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name='المستخدم', null=True, blank=True)
    title = models.CharField('العنوان', max_length=200)
    message = models.TextField('الرسالة')
    notification_type = models.CharField('النوع', max_length=20, choices=NotificationType.choices, default=NotificationType.SYSTEM)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    is_read = models.BooleanField('مقروء', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'إشعار'
        verbose_name_plural = 'الإشعارات'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
