import io
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import (
    ArabicAuthenticationForm,
    MovementFilterForm,
    ProductForm,
    StockInForm,
    StockOutForm,
    TransferForm,
    WarehouseForm,
)
from .models import MovementType, Notification, Product, StockLevel, StockMovement, Warehouse
from .barcode_utils import generate_product_barcode
from .pdf_utils import render_report_pdf
from .services import (
    StockError,
    aggregate_stock_value,
    get_product_by_barcode,
    stock_in,
    stock_out,
    stock_value_by_warehouse,
    transfer_stock,
)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = ArabicAuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('dashboard')
    return render(request, 'inventory/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    products_count = Product.objects.filter(is_active=True).count()
    warehouses_count = Warehouse.objects.filter(is_active=True).count()
    low_stock_count = Product.objects.filter(is_active=True).annotate(
        total=Sum('stock_levels__quantity')
    ).filter(total__lte=F('min_quantity')).count()

    total_stock_value = aggregate_stock_value(StockLevel.objects.select_related('product'))

    recent_movements = StockMovement.objects.select_related('product', 'user', 'warehouse')[:10]
    low_stock_products = Product.objects.filter(is_active=True).annotate(
        total=Sum('stock_levels__quantity')
    ).filter(total__lte=F('min_quantity'))[:8]

    today = timezone.localdate()
    expiry_alert_stock = StockLevel.objects.filter(
        quantity__gt=0,
        expiry_date__isnull=False,
    ).select_related('product', 'warehouse').order_by('expiry_date')
    expired_stock = [s for s in expiry_alert_stock if s.expiry_status == 'expired'][:8]
    expiring_soon_stock = [s for s in expiry_alert_stock if s.expiry_status == 'expiring_soon'][:8]

    thirty_days_ago = timezone.now() - timedelta(days=30)
    movement_stats = (
        StockMovement.objects.filter(created_at__gte=thirty_days_ago)
        .values('movement_type')
        .annotate(count=Count('id'))
        .order_by('movement_type')
    )
    chart_labels = [dict(MovementType.choices).get(item['movement_type'], item['movement_type']) for item in movement_stats]
    chart_data = [item['count'] for item in movement_stats]

    daily_movements = (
        StockMovement.objects.filter(created_at__gte=thirty_days_ago)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    line_labels = [str(item['day']) for item in daily_movements]
    line_data = [item['count'] for item in daily_movements]

    context = {
        'products_count': products_count,
        'warehouses_count': warehouses_count,
        'low_stock_count': low_stock_count,
        'total_stock_value': total_stock_value,
        'recent_movements': recent_movements,
        'low_stock_products': low_stock_products,
        'expired_stock': expired_stock,
        'expiring_soon_stock': expiring_soon_stock,
        'chart_labels_json': json.dumps(chart_labels, ensure_ascii=False),
        'chart_data_json': json.dumps(chart_data),
        'line_labels_json': json.dumps(line_labels, ensure_ascii=False),
        'line_data_json': json.dumps(line_data),
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
def product_list(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(is_active=True).annotate(total=Sum('stock_levels__quantity'))
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(barcode__icontains=query))
    return render(request, 'inventory/products/list.html', {'products': products, 'query': query})


@login_required
def product_create(request):
    form = ProductForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'تم إضافة المنتج بنجاح.')
        return redirect('product_list')
    return render(request, 'inventory/products/form.html', {'form': form, 'title': 'إضافة منتج'})


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'تم تحديث المنتج بنجاح.')
        return redirect('product_list')
    return render(request, 'inventory/products/form.html', {'form': form, 'title': 'تعديل منتج', 'product': product})


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.is_active = False
        product.save()
        messages.success(request, 'تم حذف المنتج.')
        return redirect('product_list')
    return render(request, 'inventory/products/delete.html', {'product': product})


@login_required
def product_barcode(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'inventory/products/barcode.html', {'product': product})


@login_required
def warehouse_list(request):
    warehouses = Warehouse.objects.filter(is_active=True).annotate(total=Sum('stock_levels__quantity'))
    return render(request, 'inventory/warehouses/list.html', {'warehouses': warehouses})


@login_required
def warehouse_create(request):
    form = WarehouseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'تم إضافة المستودع بنجاح.')
        return redirect('warehouse_list')
    return render(request, 'inventory/warehouses/form.html', {'form': form, 'title': 'إضافة مستودع'})


@login_required
def warehouse_edit(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    form = WarehouseForm(request.POST or None, instance=warehouse)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'تم تحديث المستودع بنجاح.')
        return redirect('warehouse_list')
    return render(request, 'inventory/warehouses/form.html', {'form': form, 'title': 'تعديل مستودع', 'warehouse': warehouse})


@login_required
def warehouse_detail(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    stock_levels = warehouse.stock_levels.select_related('product').filter(quantity__gt=0)
    low_stock = stock_levels.filter(quantity__lte=F('product__min_quantity'))
    return render(request, 'inventory/warehouses/detail.html', {
        'warehouse': warehouse,
        'stock_levels': stock_levels,
        'low_stock': low_stock,
    })


@login_required
def stock_in_view(request):
    form = StockInForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            stock_in(
                product=form.cleaned_data['product'],
                warehouse=form.cleaned_data['warehouse'],
                quantity=form.cleaned_data['quantity'],
                movement_type=form.cleaned_data['movement_type'],
                user=request.user,
                reference_number=form.cleaned_data.get('reference_number', ''),
                notes=form.cleaned_data.get('notes', ''),
                entry_date=form.cleaned_data['entry_date'],
                expiry_date=form.cleaned_data.get('expiry_date'),
                effective_date=form.cleaned_data['effective_date'],
            )
            messages.success(request, 'تمت عملية الإدخال بنجاح.')
            return redirect('movement_log')
        except StockError as exc:
            messages.error(request, str(exc))
    return render(request, 'inventory/operations/stock_in.html', {'form': form})


@login_required
def stock_out_view(request):
    form = StockOutForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            stock_out(
                product=form.cleaned_data['product'],
                warehouse=form.cleaned_data['warehouse'],
                quantity=form.cleaned_data['quantity'],
                movement_type=form.cleaned_data['movement_type'],
                user=request.user,
                reference_number=form.cleaned_data.get('reference_number', ''),
                notes=form.cleaned_data.get('notes', ''),
            )
            messages.success(request, 'تمت عملية الإخراج بنجاح.')
            return redirect('movement_log')
        except StockError as exc:
            messages.error(request, str(exc))
    return render(request, 'inventory/operations/stock_out.html', {'form': form})


@login_required
def transfer_view(request):
    form = TransferForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            transfer_stock(
                product=form.cleaned_data['product'],
                warehouse_from=form.cleaned_data['warehouse_from'],
                warehouse_to=form.cleaned_data['warehouse_to'],
                quantity=form.cleaned_data['quantity'],
                user=request.user,
                reference_number=form.cleaned_data.get('reference_number', ''),
                notes=form.cleaned_data.get('notes', ''),
            )
            messages.success(request, 'تم النقل بين المستودعات بنجاح.')
            return redirect('movement_log')
        except StockError as exc:
            messages.error(request, str(exc))
    return render(request, 'inventory/operations/transfer.html', {'form': form})


@login_required
def barcode_scanner(request):
    return render(request, 'inventory/operations/scanner.html')


@login_required
@require_GET
def api_generate_barcode(request):
    sku = request.GET.get('sku', '').strip()
    exclude_pk = request.GET.get('exclude_pk')
    barcode = generate_product_barcode(
        sku=sku,
        exclude_pk=int(exclude_pk) if exclude_pk else None,
    )
    return JsonResponse({'barcode': barcode})


@login_required
@require_GET
def api_product_by_barcode(request):
    barcode = request.GET.get('barcode', '').strip()
    product = get_product_by_barcode(barcode)
    if not product:
        return JsonResponse({'found': False, 'message': 'المنتج غير موجود'})
    stock_by_warehouse = [
        {'warehouse': s.warehouse.name, 'quantity': s.quantity}
        for s in product.stock_levels.select_related('warehouse').all()
    ]
    return JsonResponse({
        'found': True,
        'id': product.id,
        'name': product.name,
        'sku': product.sku,
        'barcode': product.barcode,
        'price': str(product.price),
        'total_quantity': product.total_quantity,
        'stock_by_warehouse': stock_by_warehouse,
    })


@login_required
def movement_log(request):
    form = MovementFilterForm(request.GET or None)
    movements = StockMovement.objects.select_related('product', 'user', 'warehouse', 'warehouse_from', 'warehouse_to')
    if form.is_valid():
        if form.cleaned_data.get('movement_type'):
            movements = movements.filter(movement_type=form.cleaned_data['movement_type'])
        if form.cleaned_data.get('warehouse'):
            wh = form.cleaned_data['warehouse']
            movements = movements.filter(Q(warehouse=wh) | Q(warehouse_from=wh) | Q(warehouse_to=wh))
        if form.cleaned_data.get('product'):
            movements = movements.filter(product=form.cleaned_data['product'])
    return render(request, 'inventory/movements/list.html', {'movements': movements[:200], 'form': form})


@login_required
def notifications_list(request):
    notifications = request.user.notifications.all()
    return render(request, 'inventory/notifications/list.html', {'notifications': notifications})


@login_required
@require_POST
def notification_mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('notifications_list')


@login_required
@require_POST
def notifications_mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, 'تم تعليم جميع الإشعارات كمقروءة.')
    return redirect('notifications_list')


@login_required
def report_current_stock(request):
    warehouse_id = request.GET.get('warehouse')
    stock_levels = StockLevel.objects.select_related('product', 'warehouse').filter(quantity__gt=0)
    if warehouse_id:
        stock_levels = stock_levels.filter(warehouse_id=warehouse_id)
    warehouses = Warehouse.objects.filter(is_active=True)
    total_value = aggregate_stock_value(stock_levels)
    return render(request, 'inventory/reports/current_stock.html', {
        'stock_levels': stock_levels,
        'warehouses': warehouses,
        'selected_warehouse': warehouse_id,
        'total_value': total_value,
    })


@login_required
def report_turnover(request):
    days = int(request.GET.get('days', 30))
    since = timezone.now() - timedelta(days=days)
    outbound = (
        StockMovement.objects.filter(
            created_at__gte=since,
            movement_type__in=[MovementType.OUT_SALE, MovementType.OUT_DISPATCH],
        )
        .values('product__name', 'product__sku')
        .annotate(total_out=Sum('quantity'))
        .order_by('-total_out')
    )
    return render(request, 'inventory/reports/turnover.html', {'outbound': outbound, 'days': days})


@login_required
def report_slow_moving(request):
    days = int(request.GET.get('days', 60))
    since = timezone.now() - timedelta(days=days)
    active_product_ids = StockMovement.objects.filter(created_at__gte=since).values_list('product_id', flat=True).distinct()
    slow_stock = (
        StockLevel.objects.filter(quantity__gt=0, product__is_active=True)
        .exclude(product_id__in=active_product_ids)
        .select_related('product', 'warehouse')
        .order_by('expiry_date', 'entry_date')
    )
    today = timezone.localdate()
    expired_stock = StockLevel.objects.filter(
        quantity__gt=0, expiry_date__lt=today,
    ).select_related('product', 'warehouse').order_by('expiry_date')
    return render(request, 'inventory/reports/slow_moving.html', {
        'slow_stock': slow_stock,
        'expired_stock': expired_stock,
        'days': days,
        'today': today,
    })


@login_required
def report_financial(request):
    stock_levels = StockLevel.objects.select_related('product', 'warehouse').filter(quantity__gt=0)
    by_warehouse = stock_value_by_warehouse(stock_levels)
    total_value = aggregate_stock_value(stock_levels)
    financial_movements = (
        StockMovement.objects.select_related('product', 'warehouse', 'user', 'warehouse_from', 'warehouse_to')
        .order_by('-created_at')[:150]
    )
    return render(request, 'inventory/reports/financial.html', {
        'by_warehouse': by_warehouse,
        'total_value': total_value,
        'stock_levels': stock_levels,
        'financial_movements': financial_movements,
        'report_generated_at': timezone.now(),
    })


def _render_pdf(report_type, context, filename):
    try:
        pdf_bytes = render_report_pdf(report_type, context)
        if not pdf_bytes:
            return None
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception:
        return None


@login_required
def report_pdf(request, report_type):
    filename = 'report.pdf'
    context = {}

    if report_type == 'current_stock':
        warehouse_id = request.GET.get('warehouse')
        stock_levels = StockLevel.objects.select_related('product', 'warehouse').filter(quantity__gt=0)
        if warehouse_id:
            stock_levels = stock_levels.filter(warehouse_id=warehouse_id)
        context = {
            'stock_levels': stock_levels,
            'total_value': aggregate_stock_value(stock_levels),
        }
        filename = 'current_stock.pdf'
    elif report_type == 'turnover':
        days = int(request.GET.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        outbound = (
            StockMovement.objects.filter(
                created_at__gte=since,
                movement_type__in=[MovementType.OUT_SALE, MovementType.OUT_DISPATCH],
            )
            .values('product__name', 'product__sku')
            .annotate(total_out=Sum('quantity'))
            .order_by('-total_out')
        )
        context = {'outbound': outbound, 'days': days}
        filename = 'turnover.pdf'
    elif report_type == 'financial':
        stock_levels = StockLevel.objects.select_related('product', 'warehouse').filter(quantity__gt=0)
        context = {
            'by_warehouse': stock_value_by_warehouse(stock_levels),
            'total_value': aggregate_stock_value(stock_levels),
            'financial_movements': StockMovement.objects.select_related(
                'product', 'warehouse', 'user',
            ).order_by('-created_at')[:80],
            'report_generated_at': timezone.now(),
        }
        filename = 'financial.pdf'
    elif report_type == 'slow_moving':
        days = int(request.GET.get('days', 60))
        since = timezone.now() - timedelta(days=days)
        active_product_ids = StockMovement.objects.filter(
            created_at__gte=since,
        ).values_list('product_id', flat=True).distinct()
        slow_stock = (
            StockLevel.objects.filter(quantity__gt=0, product__is_active=True)
            .exclude(product_id__in=active_product_ids)
            .select_related('product', 'warehouse')
            .order_by('expiry_date')
        )
        context = {
            'slow_stock': slow_stock,
            'expired_stock': StockLevel.objects.filter(
                quantity__gt=0, expiry_date__lt=timezone.localdate(),
            ).select_related('product', 'warehouse'),
            'days': days,
        }
        filename = 'slow_moving.pdf'
    else:
        messages.error(request, 'نوع التقرير غير موجود.')
        return redirect('dashboard')

    pdf_response = _render_pdf(report_type, context, filename)
    if pdf_response:
        return pdf_response
    messages.error(request, 'تعذر إنشاء ملف PDF.')
    return redirect('dashboard')
