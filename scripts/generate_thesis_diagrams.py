"""Generate thesis diagrams as a single draw.io file."""
import html
import uuid
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / 'docs' / 'Investory_Thesis_Diagrams.drawio'


def esc(text):
    return html.escape(str(text), quote=True)


def cell(cid, value='', style='', vertex=False, edge=False, parent='1', source=None, target=None, x=0, y=0, w=120, h=60):
    attrs = [f'id="{cid}"', f'parent="{parent}"']
    if value:
        attrs.append(f'value="{esc(value)}"')
    if style:
        attrs.append(f'style="{style}"')
    if vertex:
        attrs.append('vertex="1"')
    if edge:
        attrs.append('edge="1"')
    if source:
        attrs.append(f'source="{source}"')
    if target:
        attrs.append(f'target="{target}"')
    geo = f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
    if edge:
        geo = '<mxGeometry relative="1" as="geometry"/>'
    return f'        <mxCell {" ".join(attrs)}>\n          {geo}\n        </mxCell>'


def diagram(name, cells_xml):
    did = str(uuid.uuid4())
    return f'''  <diagram id="{did}" name="{esc(name)}">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="1200" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{cells_xml}
      </root>
    </mxGraphModel>
  </diagram>'''


def use_case_diagram():
    s = []
    s.append(cell('uc_sys', 'نظام Investory\nإدارة المستودعات والمخزون', 'rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=13;', True, x=320, y=60, w=520, h=640))
    actor_style = 'shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;'
    uc_style = 'ellipse;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;'
    s.append(cell('actor_admin', 'مدير المخزون', actor_style, True, x=80, y=220, w=40, h=80))
    cases = [
        ('uc1', 'تسجيل الدخول', 420, 120),
        ('uc2', 'إدارة المنتجات', 420, 190),
        ('uc3', 'إدارة المستودعات', 420, 260),
        ('uc4', 'إدخال مخزون\n(شراء / استلام)', 420, 340),
        ('uc5', 'إخراج مخزون\n(بيع / صرف)', 650, 340),
        ('uc6', 'نقل بين مستودعات', 420, 430),
        ('uc7', 'مسح الباركود', 650, 430),
        ('uc8', 'طباعة الباركود', 650, 190),
        ('uc9', 'عرض سجل الحركة', 420, 520),
        ('uc10', 'استلام التنبيهات', 650, 520),
        ('uc11', 'عرض التقارير', 420, 610),
        ('uc12', 'تصدير PDF', 650, 610),
    ]
    for cid, label, x, y in cases:
        s.append(cell(cid, label, uc_style, True, x=x, y=y, w=170, h=60))
    for cid, _, _, _ in cases:
        s.append(cell(f'e_{cid}', '', 'endArrow=classic;html=1;rounded=0;', False, True, source='actor_admin', target=cid))
    s.append(cell('actor_email', 'البريد الإلكتروني', actor_style, True, x=900, y=500, w=40, h=80))
    s.append(cell('e_email', '', 'endArrow=classic;html=1;dashed=1;', False, True, source='uc10', target='actor_email'))
    s.append(cell('note1', 'مشروع ماجستير MCS\nالجامعة الافتراضية السورية', 'text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;fontSize=11;fontColor=#666666;', True, x=80, y=20, w=260, h=40))
    return diagram('1 - Use Case | حالات الاستخدام', '\n'.join(s))


def er_diagram():
    s = []
    ent = 'swimlane;fontStyle=1;childLayout=stackLayout;horizontal=1;startSize=30;fillColor=#dae8fc;strokeColor=#6c8ebf;horizontalStack=0;resizeParent=1;'
    attr = 'text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=4;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;'
    entities = {
        'User': ['PK id', 'username', 'email', 'password'],
        'Product': ['PK id', 'name', 'SKU (unique)', 'barcode (unique)', 'price', 'min_quantity', 'shelf', 'rack_number'],
        'Warehouse': ['PK id', 'name', 'code (unique)', 'address', 'is_main', 'is_active'],
        'StockLevel': ['PK id', 'FK product_id', 'FK warehouse_id', 'quantity', 'UNIQUE(product, warehouse)'],
        'StockMovement': ['PK id', 'FK product_id', 'movement_type', 'FK warehouse_id', 'FK warehouse_from', 'FK warehouse_to', 'quantity', 'quantity_before', 'quantity_after', 'FK user_id', 'created_at'],
        'Notification': ['PK id', 'FK user_id', 'FK product_id', 'title', 'message', 'notification_type', 'is_read'],
    }
    pos = {'User': (40, 80), 'Product': (320, 80), 'Warehouse': (620, 80), 'StockLevel': (320, 380), 'StockMovement': (40, 380), 'Notification': (620, 380)}
    ids = {}
    for name, fields in entities.items():
        x, y = pos[name]
        sid = f'er_{name}'
        ids[name] = sid
        s.append(cell(sid, name, ent, True, x=x, y=y, w=220, h=30 + len(fields) * 24))
        for i, field in enumerate(fields):
            s.append(cell(f'{sid}_{i}', field, attr, True, parent=sid, x=0, y=30 + i * 24, w=220, h=24))
    rel_style = 'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=ERmany;startArrow=ERone;'
    relations = [
        ('Product', 'StockLevel'), ('Warehouse', 'StockLevel'), ('Product', 'StockMovement'),
        ('User', 'StockMovement'), ('User', 'Notification'), ('Product', 'Notification'),
    ]
    for i, (a, b) in enumerate(relations):
        s.append(cell(f'rel{i}', '1:N', rel_style, False, True, source=ids[a], target=ids[b]))
    return diagram('2 - ER Diagram | مخطط قاعدة البيانات', '\n'.join(s))


def architecture_diagram():
    s = []
    layer = 'rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontStyle=1;verticalAlign=top;spacingTop=8;'
    box = 'rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#666666;'
    s.append(cell('layer_ui', 'Presentation Layer\nطبقة العرض', layer, True, x=120, y=60, w=920, h=150))
    ui_items = ['HTML5 / CSS3', 'Bootstrap 5 RTL', 'JavaScript', 'JsBarcode', 'QuaggaJS', 'Chart.js']
    for i, item in enumerate(ui_items):
        s.append(cell(f'ui{i}', item, box, True, x=150 + i * 145, y=100, w=130, h=50))
    s.append(cell('layer_app', 'Application Layer\nطبقة التطبيق (Django)', layer, True, x=120, y=260, w=920, h=170))
    app_items = ['Views', 'Forms', 'Services', 'PDF Utils', 'Barcode Utils', 'Context Processors']
    for i, item in enumerate(app_items):
        s.append(cell(f'app{i}', item, box, True, x=150 + i * 145, y=300, w=130, h=50))
    s.append(cell('layer_data', 'Data Layer\nطبقة البيانات', layer, True, x=120, y=480, w=920, h=130))
    s.append(cell('db', 'PostgreSQL\n(investory_db)', 'shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#d5e8d4;strokeColor=#82b366;', True, x=460, y=520, w=160, h=70))
    s.append(cell('browser', 'متصفح الويب\nChrome / Edge', 'rounded=1;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;', True, x=480, y=680, w=180, h=50))
    arrow = 'endArrow=classic;html=1;rounded=0;'
    s.append(cell('a1', 'HTTP', arrow, False, True, source='browser', target='layer_ui'))
    s.append(cell('a2', '', arrow, False, True, source='layer_ui', target='layer_app'))
    s.append(cell('a3', 'ORM', arrow, False, True, source='layer_app', target='layer_data'))
    s.append(cell('title', 'Investory - System Architecture', 'text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=16;fontStyle=1;', True, x=360, y=10, w=420, h=30))
    return diagram('3 - Architecture | المعمارية', '\n'.join(s))


def dfd_level0():
    s = []
    proc = 'ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontStyle=1;'
    ext = 'rounded=0;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;'
    store = 'shape=partialRectangle;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;'
    s.append(cell('p0', '0\nنظام إدارة\nالمستودعات', proc, True, x=420, y=280, w=160, h=100))
    externals = [('e1', 'مدير المخزون', 80, 300), ('e2', 'ماسح الباركود', 80, 450), ('e3', 'البريد الإلكتروني', 820, 300)]
    for cid, label, x, y in externals:
        s.append(cell(cid, label, ext, True, x=x, y=y, w=140, h=60))
    s.append(cell('d1', 'D1: PostgreSQL', store, True, x=430, y=500, w=140, h=50))
    arrow = 'endArrow=classic;html=1;rounded=0;'
    flows = [('f1', 'بيانات المنتجات / العمليات', 'e1', 'p0'), ('f2', 'نتائج / تقارير', 'p0', 'e1'), ('f3', 'رمز الباركود', 'e2', 'p0'), ('f4', 'تنبيهات', 'p0', 'e3'), ('f5', 'حفظ / قراءة', 'p0', 'd1')]
    for i, (fid, label, src, tgt) in enumerate(flows):
        s.append(cell(fid, label, arrow, False, True, source=src, target=tgt))
    return diagram('4 - DFD Level 0 | تدفق البيانات - مستوى 0', '\n'.join(s))


def dfd_level1():
    s = []
    proc = 'ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;'
    ext = 'rounded=0;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;'
    store = 'shape=partialRectangle;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;'
    s.append(cell('mgr', 'مدير المخزون', ext, True, x=40, y=300, w=120, h=50))
    processes = [
        ('p1', '1\nإدارة\nالمنتجات', 240, 120),
        ('p2', '2\nإدارة\nالمستودعات', 240, 260),
        ('p3', '3\nعمليات\nالإدخال/الإخراج', 460, 190),
        ('p4', '4\nالباركود\nوالمسح', 460, 360),
        ('p5', '5\nالتقارير\nوالتنبيهات', 680, 190),
        ('p6', '6\nالمصادقة\nوالصلاحيات', 680, 360),
    ]
    for cid, label, x, y in processes:
        s.append(cell(cid, label, proc, True, x=x, y=y, w=120, h=80))
    stores = [('d1', 'Products', 240, 480), ('d2', 'Warehouses', 380, 480), ('d3', 'StockLevels', 520, 480), ('d4', 'Movements', 660, 480), ('d5', 'Notifications', 800, 480)]
    for cid, label, x, y in stores:
        s.append(cell(cid, label, store, True, x=x, y=y, w=110, h=40))
    arrow = 'endArrow=classic;html=1;rounded=0;'
    for i, pid in enumerate(['p1', 'p2', 'p3', 'p4', 'p5', 'p6']):
        s.append(cell(f'lm{i}', '', arrow, False, True, source='mgr', target=pid))
    return diagram('5 - DFD Level 1 | تدفق البيانات - مستوى 1', '\n'.join(s))


def activity(title, steps, page_name):
    s = []
    start = 'ellipse;whiteSpace=wrap;html=1;fillColor=#000000;strokeColor=none;fontColor=#ffffff;'
    act = 'rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;'
    decision = 'rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;'
    end = 'ellipse;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;'
    s.append(cell('start', 'بداية', start, True, x=340, y=40, w=80, h=40))
    y = 110
    prev = 'start'
    for i, step in enumerate(steps):
        cid = f'a{i}'
        style = decision if step.get('decision') else act
        h = 70 if step.get('decision') else 50
        s.append(cell(cid, step['label'], style, True, x=280, y=y, w=200, h=h))
        s.append(cell(f'e{i}', step.get('edge', ''), 'endArrow=classic;html=1;', False, True, source=prev, target=cid))
        prev = cid
        y += h + 40
    s.append(cell('end', 'نهاية', end, True, x=340, y=y, w=80, h=40))
    s.append(cell('end_e', '', 'endArrow=classic;html=1;', False, True, source=prev, target='end'))
    return diagram(page_name, '\n'.join(s))


def activity_stock_in():
    steps = [
        {'label': 'تسجيل الدخول للنظام'},
        {'label': 'فتح صفحة إدخال مخزون'},
        {'label': 'اختيار المنتج والمستودع'},
        {'label': 'اختيار نوع العملية\n(فاتورة شراء / أمر استلام)'},
        {'label': 'مسح الباركود؟', 'decision': True, 'edge': ''},
        {'label': 'إدخال الكمية ورقم المرجع'},
        {'label': 'التحقق من صحة البيانات', 'decision': True},
        {'label': 'تحديث StockLevel\n+ تسجيل StockMovement'},
        {'label': 'فحص الحد الأدنى\nوإرسال تنبيه إن لزم'},
    ]
    return activity('Stock In', steps, '6 - Activity Stock In | نشاط الإدخال')


def activity_stock_out():
    steps = [
        {'label': 'تسجيل الدخول للنظام'},
        {'label': 'فتح صفحة إخراج مخزون'},
        {'label': 'اختيار المنتج والمستودع'},
        {'label': 'اختيار فاتورة بيع\nأو أمر صرف'},
        {'label': 'التحقق: الكمية متوفرة\nفي المستودع المختار؟', 'decision': True},
        {'label': 'خصم الكمية من StockLevel'},
        {'label': 'تسجيل الحركة في Audit Log'},
        {'label': 'فحص الحد الأدنى للمخزون'},
    ]
    return activity('Stock Out', steps, '7 - Activity Sale | نشاط البيع')


def activity_transfer():
    steps = [
        {'label': 'اختيار المنتج'},
        {'label': 'تحديد المستودع المصدر\nوالمستودع الهدف'},
        {'label': 'المستودعان مختلفان؟', 'decision': True},
        {'label': 'الكمية متوفرة\nفي المصدر؟', 'decision': True},
        {'label': 'خصم من المصدر\n+ إضافة للهدف'},
        {'label': 'تسجيل حركة TRANSFER\nفي سجل الحركة'},
    ]
    return activity('Transfer', steps, '8 - Activity Transfer | نشاط النقل')


def sequence_barcode():
    s = []
    lifeline = 'shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=1;collapsible=0;recursiveResize=0;outlineConnect=0;'
    actor = 'shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;'
    participants = [
        ('u', 'المستخدم', 80, 60, actor),
        ('b', 'المتصفح\n(JsBarcode/Quagga)', 260, 60, lifeline),
        ('v', 'Django Views', 480, 60, lifeline),
        ('s', 'Services', 680, 60, lifeline),
        ('db', 'PostgreSQL', 880, 60, lifeline),
    ]
    for cid, label, x, y, style in participants:
        s.append(cell(cid, label, style, True, x=x, y=y, w=100, h=200))
    msgs = [
        (120, '1. مسح الباركود', 'u', 'b'),
        (160, '2. GET /api/product-by-barcode', 'b', 'v'),
        (200, '3. get_product_by_barcode()', 'v', 's'),
        (240, '4. SELECT Product', 's', 'db'),
        (280, '5. بيانات المنتج + المخزون', 'db', 'u'),
        (320, '6. تنفيذ إدخال/إخراج', 'u', 'v'),
        (360, '7. stock_in / stock_out', 'v', 's'),
        (400, '8. UPDATE + INSERT Movement', 's', 'db'),
    ]
    arrow = 'endArrow=block;html=1;rounded=0;'
    for i, (y, label, src, tgt) in enumerate(msgs):
        s.append(cell(f'm{i}', label, arrow, False, True, source=src, target=tgt))
    return diagram('9 - Sequence Barcode | تسلسل مسح الباركود', '\n'.join(s))


def class_diagram():
    s = []
    cls = 'swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize=26;fillColor=#dae8fc;strokeColor=#6c8ebf;'
    attr = 'text;strokeColor=none;fillColor=none;align=left;verticalAlign=top;spacingLeft=4;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;'
    classes = {
        'Product': ['- name: str', '- sku: str', '- barcode: str', '- price: Decimal', '- min_quantity: int', '+ total_quantity()', '+ is_low_stock()'],
        'Warehouse': ['- name: str', '- code: str', '- is_main: bool', '+ total_quantity()'],
        'StockLevel': ['- product: FK', '- warehouse: FK', '- quantity: int'],
        'StockMovement': ['- movement_type: str', '- quantity: int', '- quantity_before: int', '- quantity_after: int', '- user: FK'],
        'StockService': ['+ stock_in()', '+ stock_out()', '+ transfer_stock()', '+ check_low_stock()'],
    }
    pos = {'Product': (60, 60), 'Warehouse': (60, 320), 'StockLevel': (360, 190), 'StockMovement': (360, 420), 'StockService': (680, 190)}
    ids = {}
    for name, fields in classes.items():
        x, y = pos[name]
        cid = f'cl_{name}'
        ids[name] = cid
        s.append(cell(cid, name, cls, True, x=x, y=y, w=240, h=26 + len(fields) * 22))
        for i, field in enumerate(fields):
            s.append(cell(f'{cid}_{i}', field, attr, True, parent=cid, x=0, y=26 + i * 22, w=240, h=22))
    rel = 'endArrow=open;endFill=0;dashed=1;html=1;rounded=0;'
    for i, (a, b) in enumerate([('Product', 'StockLevel'), ('Warehouse', 'StockLevel'), ('StockService', 'StockMovement')]):
        s.append(cell(f'cr{i}', '', rel, False, True, source=ids[a], target=ids[b]))
    return diagram('10 - Class Diagram | مخطط الفئات', '\n'.join(s))


def gantt_diagram():
    s = []
    s.append(cell('title', 'البرنامج الزمني - 4 أشهر', 'text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=16;fontStyle=1;', True, x=400, y=20, w=300, h=30))
    tasks = [
        ('t_req', 'تحليل المتطلبات', 80, 80, 160),
        ('تصميم قاعدة البيانات', 'تصميم قاعدة البيانات', 80, 130, 160),
        ('تطوير الواجهة الخلفية', 'تطوير Backend (Django)', 80, 180, 240),
        ('تطوير الواجهات', 'تطوير واجهات المستخدم', 280, 230, 320),
        ('نظام الباركود', 'نظام الباركود', 280, 280, 200),
        ('التقارير والتنبيهات', 'التقارير والتنبيهات', 480, 280, 200),
        ('الاختبار', 'الاختبار وإصلاح الأخطاء', 480, 330, 160),
        ('التوثيق', 'التوثيق والتسليم', 640, 330, 160),
    ]
    bar = 'rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;'
    month_style = 'text;html=1;strokeColor=none;fillColor=none;fontStyle=1;'
    for i, m in enumerate(['الشهر 1', 'الشهر 2', 'الشهر 3', 'الشهر 4']):
        s.append(cell(f'm{i}', m, month_style, True, x=280 + i * 160, y=50, w=140, h=24))
    for cid, label, x, y, w in tasks:
        s.append(cell(cid, label, bar, True, x=x, y=y, w=w, h=36))
    return diagram('11 - Gantt | البرنامج الزمني', '\n'.join(s))


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    diagrams = [
        use_case_diagram(),
        er_diagram(),
        architecture_diagram(),
        dfd_level0(),
        dfd_level1(),
        activity_stock_in(),
        activity_stock_out(),
        activity_transfer(),
        sequence_barcode(),
        class_diagram(),
        gantt_diagram(),
    ]
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="app.diagrams.net" '
        'modified="2026-07-29T00:00:00.000Z" agent="Investory Thesis Generator" '
        'version="24.7.17" type="device">\n'
        + '\n'.join(diagrams)
        + '\n</mxfile>\n'
    )
    OUTPUT.write_text(content, encoding='utf-8')
    print(f'Created: {OUTPUT}')
    print(f'Pages: {len(diagrams)}')


if __name__ == '__main__':
    main()
