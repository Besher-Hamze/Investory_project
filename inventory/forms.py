from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import MovementType, Product, StockMovement, Warehouse


class ArabicAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='اسم المستخدم', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المستخدم'}))
    password = forms.CharField(label='كلمة المرور', widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'كلمة المرور'}))


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'barcode', 'price', 'min_quantity', 'shelf', 'rack_number', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'shelf': forms.TextInput(attrs={'class': 'form-control'}),
            'rack_number': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'اسم المنتج',
            'sku': 'SKU الفريد',
            'barcode': 'الباركود',
            'price': 'السعر',
            'min_quantity': 'الحد الأدنى',
            'shelf': 'الرف',
            'rack_number': 'رقم الموقع',
            'description': 'الوصف',
            'is_active': 'نشط',
        }


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'code', 'address', 'is_main', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'اسم المستودع',
            'code': 'رمز المستودع',
            'address': 'العنوان',
            'is_main': 'مستودع رئيسي',
            'is_active': 'نشط',
        }


class StockInForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        label='المنتج',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        label='المستودع',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    movement_type = forms.ChoiceField(
        choices=[(MovementType.IN_PURCHASE, 'فاتورة شراء'), (MovementType.IN_RECEIPT, 'أمر استلام')],
        label='نوع العملية',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    quantity = forms.IntegerField(min_value=1, label='الكمية', widget=forms.NumberInput(attrs={'class': 'form-control'}))
    reference_number = forms.CharField(required=False, label='رقم المرجع', widget=forms.TextInput(attrs={'class': 'form-control'}))
    notes = forms.CharField(required=False, label='ملاحظات', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))


class StockOutForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        label='المنتج',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        label='المستودع',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    movement_type = forms.ChoiceField(
        choices=[(MovementType.OUT_SALE, 'فاتورة بيع'), (MovementType.OUT_DISPATCH, 'أمر صرف')],
        label='نوع العملية',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    quantity = forms.IntegerField(min_value=1, label='الكمية', widget=forms.NumberInput(attrs={'class': 'form-control'}))
    reference_number = forms.CharField(required=False, label='رقم المرجع', widget=forms.TextInput(attrs={'class': 'form-control'}))
    notes = forms.CharField(required=False, label='ملاحظات', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))


class TransferForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        label='المنتج',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    warehouse_from = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        label='من مستودع',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    warehouse_to = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        label='إلى مستودع',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    quantity = forms.IntegerField(min_value=1, label='الكمية', widget=forms.NumberInput(attrs={'class': 'form-control'}))
    reference_number = forms.CharField(required=False, label='رقم المرجع', widget=forms.TextInput(attrs={'class': 'form-control'}))
    notes = forms.CharField(required=False, label='ملاحظات', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('warehouse_from') == cleaned.get('warehouse_to'):
            raise forms.ValidationError('يجب أن يكون المستودع المصدر مختلفاً عن المستودع الهدف.')
        return cleaned


class BarcodeScanForm(forms.Form):
    barcode = forms.CharField(label='الباركود', widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': True, 'placeholder': 'امسح أو أدخل الباركود'}))


class MovementFilterForm(forms.Form):
    movement_type = forms.ChoiceField(
        required=False,
        label='نوع العملية',
        choices=[('', 'الكل')] + list(MovementType.choices),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    warehouse = forms.ModelChoiceField(
        required=False,
        queryset=Warehouse.objects.filter(is_active=True),
        label='المستودع',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    product = forms.ModelChoiceField(
        required=False,
        queryset=Product.objects.filter(is_active=True),
        label='المنتج',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
