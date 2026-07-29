from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from inventory.models import MovementType, Product, Warehouse
from inventory.services import stock_in, stock_out, transfer_stock


class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية للمشروع'

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@investory.local', 'is_staff': True, 'is_superuser': True},
        )
        if created:
            user.set_password('admin123')
            user.save()
            self.stdout.write(self.style.SUCCESS('تم إنشاء المستخدم admin / admin123'))

        wh1, _ = Warehouse.objects.get_or_create(
            code='WH1',
            defaults={'name': 'المستودع الرئيسي', 'address': 'دمشق', 'is_main': True},
        )
        wh2, _ = Warehouse.objects.get_or_create(
            code='WH2',
            defaults={'name': 'المستودع الفرعي', 'address': 'حلب', 'is_main': False},
        )

        products_data = [
            ('شامبو مرطب', 'SKU-001', '890100001', Decimal('15000'), 10, 'A', '1'),
            ('كريم ترطيب', 'SKU-002', '890100002', Decimal('25000'), 5, 'A', '2'),
            ('سيروم شعر', 'SKU-003', '890100003', Decimal('35000'), 8, 'B', '1'),
            ('زيت argan', 'SKU-004', '890100004', Decimal('45000'), 3, 'B', '2'),
            ('غسول وجه', 'SKU-005', '890100005', Decimal('12000'), 15, 'C', '1'),
            ('بلسم شعر', 'SKU-006', '890100006', Decimal('18000'), 6, 'C', '2'),
        ]

        for name, sku, barcode, price, min_q, shelf, rack in products_data:
            Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name,
                    'barcode': barcode,
                    'price': price,
                    'min_quantity': min_q,
                    'shelf': shelf,
                    'rack_number': rack,
                },
            )

        if not user.stock_movements.exists():
            products = list(Product.objects.all())
            stock_in(products[0], wh1, 50, MovementType.IN_PURCHASE, user, 'PO-001')
            stock_in(products[1], wh1, 30, MovementType.IN_RECEIPT, user, 'RC-001')
            stock_in(products[2], wh2, 20, MovementType.IN_PURCHASE, user, 'PO-002')
            stock_in(products[3], wh1, 5, MovementType.IN_PURCHASE, user, 'PO-003')
            stock_in(products[4], wh1, 100, MovementType.IN_RECEIPT, user, 'RC-002')
            stock_in(products[5], wh2, 25, MovementType.IN_PURCHASE, user, 'PO-004')
            stock_out(products[0], wh1, 10, MovementType.OUT_SALE, user, 'INV-001')
            stock_out(products[4], wh1, 20, MovementType.OUT_DISPATCH, user, 'DISP-001')
            transfer_stock(products[1], wh1, wh2, 5, user, 'TR-001')

        self.stdout.write(self.style.SUCCESS('تم إنشاء البيانات التجريبية بنجاح.'))
