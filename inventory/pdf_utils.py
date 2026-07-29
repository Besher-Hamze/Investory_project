import io
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ARABIC_FONT_NAME = 'ArabicFont'
_FONT_REGISTERED = False


def _font_candidates():
    return [
        settings.BASE_DIR / 'static' / 'fonts' / 'Amiri-Regular.ttf',
        Path(r'C:\Windows\Fonts\tahoma.ttf'),
        Path(r'C:\Windows\Fonts\arial.ttf'),
    ]


def get_arabic_font_path():
    for path in _font_candidates():
        if path.exists():
            return path
    return None


def register_arabic_font():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return ARABIC_FONT_NAME

    font_path = get_arabic_font_path()
    if not font_path:
        raise RuntimeError('لم يتم العثور على خط يدعم العربية.')

    pdfmetrics.registerFont(TTFont(ARABIC_FONT_NAME, str(font_path)))
    _FONT_REGISTERED = True
    return ARABIC_FONT_NAME


def ar(text):
    if text is None:
        return ''
    text = str(text).strip()
    if not text:
        return text
    if not any('\u0600' <= char <= '\u06FF' for char in text):
        return text
    return get_display(arabic_reshaper.reshape(text))


def _styles():
    register_arabic_font()
    return {
        'title': ParagraphStyle(
            'Title',
            fontName=ARABIC_FONT_NAME,
            fontSize=16,
            leading=22,
            alignment=1,
            spaceAfter=12,
        ),
        'normal': ParagraphStyle(
            'Normal',
            fontName=ARABIC_FONT_NAME,
            fontSize=11,
            leading=16,
            alignment=2,
        ),
        'cell': ParagraphStyle(
            'Cell',
            fontName=ARABIC_FONT_NAME,
            fontSize=10,
            leading=14,
            alignment=2,
        ),
        'cell_center': ParagraphStyle(
            'CellCenter',
            fontName=ARABIC_FONT_NAME,
            fontSize=10,
            leading=14,
            alignment=1,
        ),
    }


def _cell(text, styles, center=False):
    style = styles['cell_center'] if center else styles['cell']
    return Paragraph(ar(text), style)


def _num(value):
    if value is None:
        return '0'
    try:
        return f'{float(value):,.2f}'
    except (TypeError, ValueError):
        return str(value)


def _table_style(header_rows=1):
    return TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, header_rows - 1), colors.HexColor('#eeeeee')),
        ('TEXTCOLOR', (0, 0), (-1, header_rows - 1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, header_rows), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ])


def _build_pdf(title, subtitle, table_data, col_widths):
    buffer = io.BytesIO()
    styles = _styles()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=ar(title),
    )
    story = [
        Paragraph(ar(title), styles['title']),
    ]
    if subtitle:
        story.append(Paragraph(ar(subtitle), styles['normal']))
    story.append(Spacer(1, 0.4 * cm))
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_table_style())
    story.append(table)
    doc.build(story)
    return buffer.getvalue()


def build_financial_pdf(by_warehouse, total_value):
    rows = [[_cell('المستودع', _styles(), center=True), _cell('القيمة (ل.س)', _styles(), center=True)]]
    for row in by_warehouse:
        rows.append([
            _cell(row['warehouse__name'], _styles()),
            Paragraph(_num(row['value']), _styles()['cell']),
        ])
    rows.append([
        _cell('الإجمالي', _styles()),
        Paragraph(_num(total_value), _styles()['cell']),
    ])
    return _build_pdf('تقرير المخزون المالي', '', rows, [10 * cm, 6 * cm])


def build_current_stock_pdf(stock_levels, total_value):
    rows = [[
        _cell('المستودع', _styles(), center=True),
        _cell('المنتج', _styles(), center=True),
        _cell('SKU', _styles(), center=True),
        _cell('الكمية', _styles(), center=True),
        _cell('السعر', _styles(), center=True),
    ]]
    for item in stock_levels:
        rows.append([
            _cell(item.warehouse.name, _styles()),
            _cell(item.product.name, _styles()),
            Paragraph(item.product.sku, _styles()['cell']),
            Paragraph(str(item.quantity), _styles()['cell']),
            Paragraph(_num(item.product.price), _styles()['cell']),
        ])
    subtitle = f'إجمالي القيمة: {_num(total_value)} ل.س'
    return _build_pdf('تقرير المخزون الحالي', subtitle, rows, [3.5 * cm, 4 * cm, 3 * cm, 2.5 * cm, 3 * cm])


def build_turnover_pdf(outbound, days):
    rows = [[
        _cell('المنتج', _styles(), center=True),
        _cell('SKU', _styles(), center=True),
        _cell('إجمالي الإخراج', _styles(), center=True),
    ]]
    for row in outbound:
        rows.append([
            _cell(row['product__name'], _styles()),
            Paragraph(row['product__sku'], _styles()['cell']),
            Paragraph(str(row['total_out']), _styles()['cell']),
        ])
    return _build_pdf('تقرير دوران المخزون', f'الفترة: {days} يوم', rows, [7 * cm, 4 * cm, 4 * cm])


def build_slow_moving_pdf(slow_products, days):
    rows = [[
        _cell('المنتج', _styles(), center=True),
        _cell('SKU', _styles(), center=True),
        _cell('الكمية الحالية', _styles(), center=True),
        _cell('الحد الأدنى', _styles(), center=True),
    ]]
    for product in slow_products:
        rows.append([
            _cell(product.name, _styles()),
            Paragraph(product.sku, _styles()['cell']),
            Paragraph(str(product.total or 0), _styles()['cell']),
            Paragraph(str(product.min_quantity), _styles()['cell']),
        ])
    return _build_pdf('تقرير المنتجات بطيئة الحركة', f'الفترة: {days} يوم', rows, [6 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm])


def render_report_pdf(report_type, context):
    builders = {
        'financial': lambda ctx: build_financial_pdf(ctx['by_warehouse'], ctx['total_value']),
        'current_stock': lambda ctx: build_current_stock_pdf(ctx['stock_levels'], ctx['total_value']),
        'turnover': lambda ctx: build_turnover_pdf(ctx['outbound'], ctx['days']),
        'slow_moving': lambda ctx: build_slow_moving_pdf(ctx['slow_products'], ctx['days']),
    }
    builder = builders.get(report_type)
    if not builder:
        return None
    return builder(context)
