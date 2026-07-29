from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Sum
from decimal import Decimal

from .models import (
    MovementType,
    Notification,
    NotificationType,
    Product,
    StockLevel,
    StockMovement,
    Warehouse,
)


class StockError(Exception):
    pass


def stock_line_value_expr():
    return F('quantity') * F('product__price')


def aggregate_stock_value(queryset):
    result = queryset.aggregate(value=Sum(stock_line_value_expr()))['value']
    return result or Decimal('0')


def stock_value_by_warehouse(queryset):
    return (
        queryset.annotate(line_value=stock_line_value_expr())
        .values('warehouse__name')
        .annotate(quantity=Sum('quantity'), value=Sum('line_value'))
        .order_by('warehouse__name')
    )


def get_or_create_stock(product, warehouse):
    stock, _ = StockLevel.objects.get_or_create(product=product, warehouse=warehouse, defaults={'quantity': 0})
    return stock


def check_low_stock(product):
    total = product.total_quantity
    if total <= product.min_quantity:
        title = f'تنبيه: مخزون منخفض - {product.name}'
        message = (
            f'المنتج "{product.name}" (SKU: {product.sku}) وصل للحد الأدنى.\n'
            f'الكمية الحالية: {total} | الحد الأدنى: {product.min_quantity}'
        )
        for user in User.objects.filter(is_active=True):
            Notification.objects.get_or_create(
                user=user,
                product=product,
                notification_type=NotificationType.LOW_STOCK,
                is_read=False,
                defaults={'title': title, 'message': message},
            )
        send_mail(
            subject=title,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.LOW_STOCK_ALERT_EMAIL],
            fail_silently=True,
        )


@transaction.atomic
def stock_in(product, warehouse, quantity, movement_type, user, reference_number='', notes=''):
    if movement_type not in (MovementType.IN_PURCHASE, MovementType.IN_RECEIPT):
        raise StockError('نوع عملية إدخال غير صالح.')

    stock = get_or_create_stock(product, warehouse)
    quantity_before = stock.quantity
    stock.quantity += quantity
    stock.save()

    movement = StockMovement.objects.create(
        product=product,
        movement_type=movement_type,
        warehouse=warehouse,
        quantity=quantity,
        quantity_before=quantity_before,
        quantity_after=stock.quantity,
        reference_number=reference_number,
        notes=notes,
        user=user,
    )
    check_low_stock(product)
    return movement


@transaction.atomic
def stock_out(product, warehouse, quantity, movement_type, user, reference_number='', notes=''):
    if movement_type not in (MovementType.OUT_SALE, MovementType.OUT_DISPATCH):
        raise StockError('نوع عملية إخراج غير صالح.')

    stock = get_or_create_stock(product, warehouse)
    if stock.quantity < quantity:
        raise StockError(f'الكمية غير كافية. المتاح: {stock.quantity}')

    quantity_before = stock.quantity
    stock.quantity -= quantity
    stock.save()

    movement = StockMovement.objects.create(
        product=product,
        movement_type=movement_type,
        warehouse=warehouse,
        quantity=quantity,
        quantity_before=quantity_before,
        quantity_after=stock.quantity,
        reference_number=reference_number,
        notes=notes,
        user=user,
    )
    check_low_stock(product)
    return movement


@transaction.atomic
def transfer_stock(product, warehouse_from, warehouse_to, quantity, user, reference_number='', notes=''):
    if warehouse_from == warehouse_to:
        raise StockError('لا يمكن النقل لنفس المستودع.')

    source = get_or_create_stock(product, warehouse_from)
    if source.quantity < quantity:
        raise StockError(f'الكمية غير كافية في {warehouse_from.name}. المتاح: {source.quantity}')

    destination = get_or_create_stock(product, warehouse_to)

    source_before = source.quantity
    source.quantity -= quantity
    source.save()

    dest_before = destination.quantity
    destination.quantity += quantity
    destination.save()

    movement = StockMovement.objects.create(
        product=product,
        movement_type=MovementType.TRANSFER,
        warehouse_from=warehouse_from,
        warehouse_to=warehouse_to,
        quantity=quantity,
        quantity_before=source_before,
        quantity_after=source.quantity,
        reference_number=reference_number,
        notes=notes or f'الوجهة: {dest_before} → {destination.quantity}',
        user=user,
    )
    check_low_stock(product)
    return movement


def get_product_by_barcode(barcode):
    barcode = barcode.strip()
    try:
        return Product.objects.get(barcode=barcode, is_active=True)
    except Product.DoesNotExist:
        return Product.objects.filter(sku__iexact=barcode, is_active=True).first()
