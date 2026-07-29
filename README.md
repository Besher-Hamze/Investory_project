# Investory - نظام إدارة المستودعات والمخزون

مشروع ماجستير MCS - الجامعة الافتراضية السورية

## الميزات

- إدارة المنتجات (اسم، SKU، باركود، سعر، كمية، حد أدنى، موقع في المستودع)
- مستودعات متعددة (رئيسي + فرعي) مع نقل المخزون بينها
- عمليات دخول: فاتورة شراء، أمر استلام
- عمليات خروج: فاتورة بيع، أمر صرف
- باركود: إنشاء (JsBarcode) + مسح بالكاميرا (QuaggaJS)
- سجل حركة (Audit Log): وقت، مستخدم، الكمية قبل وبعد
- تنبيهات عند الحد الأدنى (إشعار داخلي + بريد)
- تقارير: المخزون الحالي، دوران المخزون، بطيء الحركة، المخزون المالي (PDF)

## التقنيات

- Django 5 + PostgreSQL
- HTML, CSS, Bootstrap 5, JavaScript
- JsBarcode, QuaggaJS, Chart.js
- xhtml2pdf (بديل Dompdf لطباعة التقارير)

## التشغيل

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

افتح: http://127.0.0.1:8000

**تسجيل الدخول:**
- المستخدم: `admin`
- كلمة المرور: `admin123`

## إعداد قاعدة البيانات

عدّل ملف `.env`:

```
DB_NAME=investory_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

## الطالب

برالنت محمد رامي البيك - brlant_334658@svuonline.org

## المشرف

د. محمد مازن المصطفى - T_mmustafa@svuonline.org
