from django import forms
from django.db.models import Q
from django.utils import timezone

from inventory.models import Business, Product, Warehouse

from .models import PurchaseOrder, PurchaseOrderItem


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ('name', 'contact_email', 'contact_phone', 'notes')
        labels = {
            'name': 'Tedarikçi adı',
            'contact_email': 'E-posta adresi',
            'contact_phone': 'Telefon numarası',
            'notes': 'Notlar',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Örn. Atlas Coffee Import'}),
            'contact_email': forms.EmailInput(attrs={'placeholder': 'satin-alma@firma.com'}),
            'contact_phone': forms.TextInput(attrs={'placeholder': '+90 212 000 00 00'}),
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Teslimat, ödeme veya kalite ile ilgili notlar',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class SupplierProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('name', 'category', 'unit')
        labels = {
            'name': 'Ürün adı',
            'category': 'Kategori',
            'unit': 'Birim',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Örn. Guatemala Antigua Green'}),
            'category': forms.TextInput(attrs={'placeholder': 'Örn. Yeşil kahve'}),
        }

    def __init__(self, *args, supplier, **kwargs):
        self.supplier = supplier
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['unit'].widget.attrs['class'] = 'form-select'

    def clean_name(self):
        name = self.cleaned_data['name']
        existing_products = self.supplier.products.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            existing_products = existing_products.exclude(pk=self.instance.pk)
        if existing_products.exists():
            raise forms.ValidationError('Bu tedarikçi için aynı isimde bir ürün zaten var.')
        return name


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ('supplier', 'expected_delivery_date', 'notes')
        labels = {
            'supplier': 'Tedarikçi',
            'expected_delivery_date': 'Beklenen teslimat tarihi',
            'notes': 'Sipariş notu',
        }
        widgets = {
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Teslimat adresi, ödeme notu veya özel talep',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        supplier_queryset = Business.objects.filter(
            business_type=Business.BusinessType.SUPPLIER,
            is_active=True,
        )
        if self.instance and self.instance.supplier_id:
            supplier_queryset = Business.objects.filter(
                Q(pk=self.instance.supplier_id)
                | Q(
                    business_type=Business.BusinessType.SUPPLIER,
                    is_active=True,
                )
            )
        self.fields['supplier'].queryset = supplier_queryset.order_by('name')
        self.fields['supplier'].widget.attrs['class'] = 'form-select'
        self.fields['expected_delivery_date'].widget.attrs['class'] = 'form-control'
        self.fields['notes'].widget.attrs['class'] = 'form-control'

    def clean_supplier(self):
        supplier = self.cleaned_data['supplier']
        if (
            self.instance
            and self.instance.pk
            and self.instance.supplier_id != supplier.pk
            and self.instance.items.exists()
        ):
            raise forms.ValidationError(
                'Sipariş kalemleri eklendikten sonra tedarikçi değiştirilemez.'
            )
        return supplier


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ('product', 'quantity_ordered', 'unit_price')
        labels = {
            'product': 'Ürün',
            'quantity_ordered': 'Sipariş miktarı',
            'unit_price': 'Birim fiyat (₺)',
        }
        widgets = {
            'quantity_ordered': forms.NumberInput(attrs={'min': '0.001', 'step': '0.001'}),
            'unit_price': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
        }

    def __init__(self, *args, purchase_order, **kwargs):
        self.purchase_order = purchase_order
        super().__init__(*args, **kwargs)
        if not self.instance.purchase_order_id:
            self.instance.purchase_order = purchase_order
        products = Product.objects.filter(business=purchase_order.supplier)
        if self.instance and self.instance.product_id:
            products = products | Product.objects.filter(pk=self.instance.product_id)

        self.fields['product'].queryset = products.order_by('name').distinct()
        self.fields['product'].widget.attrs['class'] = 'form-select'
        self.fields['quantity_ordered'].widget.attrs['class'] = 'form-control'
        self.fields['unit_price'].widget.attrs['class'] = 'form-control'

    def clean_product(self):
        product = self.cleaned_data['product']
        existing_items = self.purchase_order.items.filter(product=product)
        if self.instance and self.instance.pk:
            existing_items = existing_items.exclude(pk=self.instance.pk)
        if existing_items.exists():
            raise forms.ValidationError('Bu ürün siparişte zaten var; mevcut kalemi düzenleyin.')
        return product


class GoodsReceiptForm(forms.Form):
    quantity_received = forms.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=0.001,
        label='Teslim alınan miktar',
        widget=forms.NumberInput(attrs={'min': '0.001', 'step': '0.001'}),
    )
    lot_code = forms.CharField(
        max_length=100,
        label='Lot kodu',
        widget=forms.TextInput(attrs={'placeholder': 'Örn. ETH-2026-08-A'}),
    )
    expiry_date = forms.DateField(
        label='Son kullanma tarihi',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(),
        required=False,
        empty_label='Depo seçilmedi',
        label='Teslim alınan depo',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['warehouse'].queryset = Warehouse.objects.filter(is_active=True)
        self.fields['warehouse'].widget.attrs['class'] = 'form-select'
        for name in ('quantity_received', 'lot_code', 'expiry_date'):
            self.fields[name].widget.attrs['class'] = 'form-control'

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data['expiry_date']
        if expiry_date < timezone.localdate():
            raise forms.ValidationError('Son kullanma tarihi geçmişte olamaz.')
        return expiry_date
