import uuid

from django.db.models import Max

# بادئة داخلية للشركة (EAN-13)
BARCODE_PREFIX = '629'


def ean13_check_digit(code12: str) -> str:
    total = 0
    for index, digit in enumerate(code12):
        weight = 1 if index % 2 == 0 else 3
        total += int(digit) * weight
    return str((10 - (total % 10)) % 10)


def _sku_to_body(sku: str) -> str:
    digits = ''.join(char for char in sku if char.isdigit())
    if digits:
        return digits.zfill(9)[:9]
    alnum = ''.join(char for char in sku.upper() if char.isalnum())
    if alnum:
        numeric = sum(ord(char) for char in alnum) % 1_000_000_000
        return str(numeric).zfill(9)[:9]
    return '000000001'


def build_ean13(body9: str) -> str:
    code12 = f'{BARCODE_PREFIX}{body9.zfill(9)[:9]}'
    return code12 + ean13_check_digit(code12)


def _is_available(barcode: str, exclude_pk=None) -> bool:
    from .models import Product
    qs = Product.objects.filter(barcode=barcode)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return not qs.exists()


def generate_product_barcode(sku='', exclude_pk=None) -> str:
    """توليد باركود EAN-13 فريد من SKU أو تسلسل تلقائي."""
    if sku:
        base_body = _sku_to_body(sku)
        for offset in range(100):
            body = str((int(base_body) + offset) % 1_000_000_000).zfill(9)
            barcode = build_ean13(body)
            if _is_available(barcode, exclude_pk):
                return barcode

    from .models import Product
    last_id = Product.objects.aggregate(max_id=Max('id'))['max_id'] or 0
    for offset in range(1, 1000):
        body = str(last_id + offset).zfill(9)[:9]
        barcode = build_ean13(body)
        if _is_available(barcode, exclude_pk):
            return barcode

    return uuid.uuid4().hex[:12].upper()
