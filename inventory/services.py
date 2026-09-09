from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

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


def _update_stock_dates(stock, entry_date=None, expiry_date=None, effective_date=None):
    if entry_date:
        stock.entry_date = entry_date
    if expiry_date:
        stock.expiry_date = expiry_date
    if effective_date:
        stock.effective_date = effective_date


def _validate_dates(entry_date, expiry_date, effective_date):
    if expiry_date and entry_date and entry_date > expiry_date:
        raise StockError('تاريخ الإدخال لا يمكن أن يكون بعد تاريخ الصلاحية.')
    if expiry_date and effective_date and effective_date > expiry_date:
        raise StockError('تاريخ الفاعلية لا يمكن أن يكون بعد تاريخ الصلاحية.')
    if entry_date and effective_date and effective_date < entry_date:
        raise StockError('تاريخ الفاعلية لا يمكن أن يكون قبل تاريخ الإدخال.')


def _notify_users(title, message, notification_type, product):
    for user in User.objects.filter(is_active=True):
        Notification.objects.create(
            user=user,
            product=product,
            notification_type=notification_type,
            title=title,
            message=message,
        )
    send_mail(
        subject=title,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.LOW_STOCK_ALERT_EMAIL],
        fail_silently=True,
    )


def check_low_stock(product):
    total = product.total_quantity
    if total > product.min_quantity:
        return
    title = f'تنبيه: مخزون منخفض - {product.name}'
    message = (
        f'المنتج "{product.name}" (SKU: {product.sku}) وصل للحد الأدنى.\n'
        f'الكمية الحالية: {total} | الحد الأدنى: {product.min_quantity}'
    )
    if not Notification.objects.filter(
        product=product, notification_type=NotificationType.LOW_STOCK, is_read=False,
    ).exists():
        _notify_users(title, message, NotificationType.LOW_STOCK, product)


def check_expiry(stock_level):
    if not stock_level.expiry_date or stock_level.quantity <= 0:
        return

    product = stock_level.product
    today = timezone.localdate()
    wh = stock_level.warehouse.name

    if stock_level.expiry_date < today:
        title = f'تنبيه: منتج منتهي الصلاحية - {product.name}'
        message = (
            f'المنتج "{product.name}" في {wh} منتهي الصلاحية.\n'
            f'تاريخ الصلاحية: {stock_level.expiry_date}\n'
            f'الكمية: {stock_level.quantity} — يرجى الإتلاف عبر عملية "إتلاف منتهي الصلاحية".'
        )
        ntype = NotificationType.EXPIRED
    elif stock_level.expiry_date <= today + timedelta(days=30):
        days_left = (stock_level.expiry_date - today).days
        title = f'تنبيه: قرب انتهاء الصلاحية - {product.name}'
        message = (
            f'المنتج "{product.name}" في {wh} يقترب من انتهاء الصلاحية.\n'
            f'تاريخ الصلاحية: {stock_level.expiry_date} | متبقي: {days_left} يوم\n'
            f'الكمية: {stock_level.quantity}'
        )
        ntype = NotificationType.EXPIRY_SOON
    else:
        return

    if Notification.objects.filter(
        product=product,
        notification_type=ntype,
        is_read=False,
        message__contains=str(stock_level.expiry_date),
    ).exists():
        return
    _notify_users(title, message, ntype, product)


def check_all_expiry_alerts():
    for stock in StockLevel.objects.filter(quantity__gt=0).select_related('product', 'warehouse'):
        check_expiry(stock)


@transaction.atomic
def stock_in(
    product, warehouse, quantity, movement_type, user,
    reference_number='', notes='',
    entry_date=None, expiry_date=None, effective_date=None,
):
    if movement_type not in (MovementType.IN_PURCHASE, MovementType.IN_RECEIPT):
        raise StockError('نوع عملية إدخال غير صالح.')

    today = timezone.localdate()
    entry_date = entry_date or today
    effective_date = effective_date or entry_date
    _validate_dates(entry_date, expiry_date, effective_date)

    stock = get_or_create_stock(product, warehouse)
    quantity_before = stock.quantity
    stock.quantity += quantity
    _update_stock_dates(stock, entry_date, expiry_date, effective_date)
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
        entry_date=entry_date,
        expiry_date=expiry_date,
        effective_date=effective_date,
        user=user,
    )
    check_low_stock(product)
    check_expiry(stock)
    return movement


@transaction.atomic
def stock_out(product, warehouse, quantity, movement_type, user, reference_number='', notes=''):
    if movement_type not in (MovementType.OUT_SALE, MovementType.OUT_DISPATCH, MovementType.OUT_EXPIRED):
        raise StockError('نوع عملية إخراج غير صالح.')

    stock = get_or_create_stock(product, warehouse)
    if stock.quantity < quantity:
        raise StockError(f'الكمية غير كافية. المتاح: {stock.quantity}')

    today = timezone.localdate()
    if movement_type == MovementType.OUT_SALE:
        if stock.effective_date and stock.effective_date > today:
            raise StockError(f'المنتج لم يفعّل بعد. تاريخ الفاعلية: {stock.effective_date}')
        if stock.expiry_date and stock.expiry_date < today:
            raise StockError('لا يمكن بيع منتج منتهي الصلاحية. استخدم "إتلاف منتهي الصلاحية".')
    if movement_type == MovementType.OUT_EXPIRED:
        if stock.expiry_date and stock.expiry_date >= today:
            raise StockError('هذا الخيار للمواد منتهية الصلاحية فقط.')
        notes = notes or f'إتلاف بسبب انتهاء الصلاحية: {stock.expiry_date or "غير محدد"}'

    quantity_before = stock.quantity
    stock.quantity -= quantity
    if stock.quantity == 0:
        stock.entry_date = None
        stock.expiry_date = None
        stock.effective_date = None
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

    saved_entry = source.entry_date
    saved_expiry = source.expiry_date
    saved_effective = source.effective_date

    source_before = source.quantity
    source.quantity -= quantity
    if source.quantity == 0:
        source.entry_date = None
        source.expiry_date = None
        source.effective_date = None
    source.save()

    dest_before = destination.quantity
    destination.quantity += quantity
    if saved_entry or saved_expiry or saved_effective:
        _update_stock_dates(
            destination,
            saved_entry or destination.entry_date,
            saved_expiry or destination.expiry_date,
            saved_effective or destination.effective_date,
        )
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
        entry_date=destination.entry_date,
        expiry_date=destination.expiry_date,
        effective_date=destination.effective_date,
        user=user,
    )
    check_low_stock(product)
    check_expiry(destination)
    return movement


def get_product_by_barcode(barcode):
    barcode = barcode.strip()
    try:
        return Product.objects.get(barcode=barcode, is_active=True)
    except Product.DoesNotExist:
        return Product.objects.filter(sku__iexact=barcode, is_active=True).first()
