from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from inventory.models import Business, Lot, Product, Warehouse
from purchasing.models import GoodsReceipt, PurchaseOrder, PurchaseOrderItem
from purchasing.services import receive_goods


class Command(BaseCommand):
    help = (
        'Satın alma ekranı için idempotent tedarikçi, ürün, sipariş ve teslimat '
        'demo verisi oluşturur. Mevcut kullanıcı kayıtlarını silmez.'
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            warehouses = self._ensure_warehouses()
            suppliers = self._ensure_suppliers()
            products = self._ensure_products(suppliers)
            self._ensure_orders(suppliers, products, warehouses)

        self.stdout.write(self.style.SUCCESS(
            'Satın alma demo verisi hazır: tedarikçiler, katalog ürünleri ve farklı sipariş durumları eklendi.'
        ))

    def _ensure_warehouses(self):
        warehouses = {}
        for name, city in (
            ('Ana Depo', 'İstanbul'),
            ('Kavurma Deposu', 'İstanbul'),
        ):
            warehouse, _ = Warehouse.objects.get_or_create(
                name=name,
                defaults={'city': city, 'is_active': True},
            )
            warehouses[name] = warehouse
        return warehouses

    def _ensure_suppliers(self):
        supplier_data = (
            ('Brazil Farms Co', 'brazil@example.com', '+55 11 5555 0101', True,
             'Santos ve Cerrado çekirdeklerinde düzenli konteyner sevkiyatı.'),
            ('Ethiopia Highlands Coop', 'ethiopia@example.com', '+251 11 555 0202', True,
             'Yıkanmış Yirgacheffe lotları için sezonluk tedarikçi.'),
            ('Colombia Sierra Trading', 'colombia@example.com', '+57 1 555 0303', True,
             'Supremo kalite çekirdeklerde uzun dönem tedarikçi.'),
            ('Guatemala Huehuetenango Export', 'orders@guatemala-demo.example', '+502 2222 0404', True,
             'Antigua ve Huehuetenango mikro lotları.'),
            ('Kenya Kirinyaga Estate', 'trade@kenya-demo.example', '+254 20 555 0505', True,
             'Yüksek asiditeli AA kalite Kenya çekirdekleri.'),
            ('Rwanda Nyamasheke Coop', 'supply@rwanda-demo.example', '+250 788 555 060', True,
             'Kooperatiften izlenebilir tek köken çekirdekler.'),
            ('Peru Valle Sagrado', 'export@peru-demo.example', '+51 1 555 0707', True,
             'Organik sertifikalı yeşil kahve tedarikçisi.'),
            ('Anatolia Coffee Packaging', 'sales@anatolia-demo.example', '+90 212 555 0808', True,
             'Valfli paket ve ambalaj malzemeleri.'),
            ('Legacy Origin Traders', 'archive@legacy-demo.example', '+90 216 555 0909', False,
             'Geçmiş siparişleri korunan, yeni alıma kapalı tedarikçi.'),
        )
        suppliers = {}
        for name, email, phone, is_active, notes in supplier_data:
            supplier, created = Business.objects.get_or_create(
                name=name,
                business_type=Business.BusinessType.SUPPLIER,
                defaults={
                    'contact_email': email,
                    'contact_phone': phone,
                    'is_active': is_active,
                    'notes': notes,
                },
            )
            if created:
                self.stdout.write(f'  + Tedarikçi: {supplier.name}')
            suppliers[name] = supplier
        return suppliers

    def _ensure_products(self, suppliers):
        product_data = (
            ('Brazil Farms Co', 'Brazil Cerrado Green', 'Yeşil kahve', Product.Unit.KILOGRAM),
            ('Guatemala Huehuetenango Export', 'Guatemala Antigua Green', 'Yeşil kahve', Product.Unit.KILOGRAM),
            ('Guatemala Huehuetenango Export', 'Guatemala Huehuetenango Green', 'Yeşil kahve', Product.Unit.KILOGRAM),
            ('Kenya Kirinyaga Estate', 'Kenya Kirinyaga AA Green', 'Yeşil kahve', Product.Unit.KILOGRAM),
            ('Rwanda Nyamasheke Coop', 'Rwanda Nyamasheke Green', 'Yeşil kahve', Product.Unit.KILOGRAM),
            ('Peru Valle Sagrado', 'Peru Organic Green', 'Yeşil kahve', Product.Unit.KILOGRAM),
            ('Anatolia Coffee Packaging', '250 g Valfli Kahve Paketi', 'Ambalaj', Product.Unit.PIECE),
            ('Anatolia Coffee Packaging', '1 kg Valfli Kahve Paketi', 'Ambalaj', Product.Unit.PIECE),
            ('Legacy Origin Traders', 'Legacy Sumatra Green', 'Yeşil kahve', Product.Unit.KILOGRAM),
        )
        products = {
            product.name: product
            for product in Product.objects.filter(
                business__business_type=Business.BusinessType.SUPPLIER
            )
        }
        for supplier_name, name, category, unit in product_data:
            product, created = Product.objects.get_or_create(
                name=name,
                business=suppliers[supplier_name],
                defaults={'category': category, 'unit': unit},
            )
            if created:
                self.stdout.write(f'  + Katalog ürünü: {product.name}')
            products[name] = product
        return products

    def _order(self, supplier, code, status, expected_delivery_date, note):
        order, created = PurchaseOrder.objects.get_or_create(
            supplier=supplier,
            notes=f'[DEMO:{code}] {note}',
            defaults={
                'status': status,
                'expected_delivery_date': expected_delivery_date,
            },
        )
        if created:
            self.stdout.write(f'  + Sipariş: {code} ({order.get_status_display()})')
        return order

    @staticmethod
    def _item(order, product, quantity, unit_price):
        item, _ = PurchaseOrderItem.objects.get_or_create(
            purchase_order=order,
            product=product,
            defaults={
                'quantity_ordered': Decimal(str(quantity)),
                'unit_price': Decimal(str(unit_price)),
            },
        )
        return item

    def _receipt(self, order, item, quantity, lot_code, expiry_date, warehouse):
        if GoodsReceipt.objects.filter(
            purchase_order_item=item,
            lot__lot_code=lot_code,
        ).exists():
            return

        # Teslim alma servisi yalnızca gönderilmiş/teyitli siparişleri kabul eder.
        if order.status not in (
            PurchaseOrder.Status.SENT,
            PurchaseOrder.Status.CONFIRMED,
            PurchaseOrder.Status.PARTIALLY_RECEIVED,
        ):
            order.status = PurchaseOrder.Status.CONFIRMED
            order.save(update_fields=['status', 'updated_at'])

        # Sabit demo lot kodu başka bir kayda aitse sessizce veri bozmamak için durur.
        if Lot.objects.filter(product=item.product, lot_code=lot_code).exists():
            self.stdout.write(self.style.WARNING(
                f'  ! {lot_code} lot kodu başka bir kayıtta kullanılıyor; teslim kaydı atlandı.'
            ))
            return

        receive_goods(
            item,
            quantity_received=Decimal(str(quantity)),
            lot_code=lot_code,
            expiry_date=expiry_date,
            warehouse=warehouse,
        )

    def _ensure_orders(self, suppliers, products, warehouses):
        today = timezone.localdate()
        expiry = today + timedelta(days=330)

        brazil = self._order(
            suppliers['Brazil Farms Co'], 'PO-001', PurchaseOrder.Status.RECEIVED,
            today - timedelta(days=14), 'Çok kalemli tamamlanmış yeşil kahve alımı.',
        )
        brazil_santos = products['Brazil Santos Green']
        brazil_cerrado = products['Brazil Cerrado Green']
        self._receipt(
            brazil,
            self._item(brazil, brazil_santos, '220', '43.50'),
            '220', 'DEMO-BR-2026-001', expiry, warehouses['Ana Depo'],
        )
        self._receipt(
            brazil,
            self._item(brazil, brazil_cerrado, '140', '46.00'),
            '140', 'DEMO-BR-2026-002', expiry, warehouses['Ana Depo'],
        )

        guatemala = self._order(
            suppliers['Guatemala Huehuetenango Export'], 'PO-002', PurchaseOrder.Status.CONFIRMED,
            today + timedelta(days=4), 'İki sevkiyatlı mikro lot alımı; ilk parti teslim alındı.',
        )
        guatemala_antigua = self._item(
            guatemala, products['Guatemala Antigua Green'], '120', '69.50'
        )
        self._item(guatemala, products['Guatemala Huehuetenango Green'], '80', '72.00')
        self._receipt(
            guatemala, guatemala_antigua, '60', 'DEMO-GT-2026-001-A',
            expiry, warehouses['Kavurma Deposu'],
        )

        kenya = self._order(
            suppliers['Kenya Kirinyaga Estate'], 'PO-003', PurchaseOrder.Status.CONFIRMED,
            today + timedelta(days=7), 'Tedarikçi teyidi beklenen Kenya AA alımı.',
        )
        self._item(kenya, products['Kenya Kirinyaga AA Green'], '90', '88.00')

        rwanda = self._order(
            suppliers['Rwanda Nyamasheke Coop'], 'PO-004', PurchaseOrder.Status.SENT,
            today - timedelta(days=2), 'Gönderildi; beklenen teslim tarihi geçti.',
        )
        self._item(rwanda, products['Rwanda Nyamasheke Green'], '100', '74.00')

        peru = self._order(
            suppliers['Peru Valle Sagrado'], 'PO-005', PurchaseOrder.Status.DRAFT,
            today + timedelta(days=16), 'İç onay bekleyen organik kahve taslağı.',
        )
        self._item(peru, products['Peru Organic Green'], '110', '67.00')

        packaging = self._order(
            suppliers['Anatolia Coffee Packaging'], 'PO-006', PurchaseOrder.Status.CANCELLED,
            today - timedelta(days=6), 'Fiyat revizyonu nedeniyle iptal edilen ambalaj siparişi.',
        )
        self._item(packaging, products['250 g Valfli Kahve Paketi'], '5000', '3.20')
        self._item(packaging, products['1 kg Valfli Kahve Paketi'], '1200', '4.80')

        legacy = self._order(
            suppliers['Legacy Origin Traders'], 'PO-007', PurchaseOrder.Status.RECEIVED,
            today - timedelta(days=28), 'Geçmiş tedarikçiye ait tamamlanmış referans sipariş.',
        )
        legacy_item = self._item(legacy, products['Legacy Sumatra Green'], '70', '61.00')
        self._receipt(
            legacy, legacy_item, '70', 'DEMO-LG-2026-001',
            expiry, warehouses['Ana Depo'],
        )
