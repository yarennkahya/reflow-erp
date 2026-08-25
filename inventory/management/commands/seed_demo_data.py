from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from inventory.models import Business, Product
from purchasing.models import PurchaseOrder, PurchaseOrderItem
from purchasing.services import receive_goods
from production.models import Recipe, RecipeComponent
from production.services import create_roast_batch
from sales.models import Customer, Order, OrderItem
from sales.services import fulfill_order
from ai_layer.models import Document


class Command(BaseCommand):
    help = (
        'Zengin bir demo veri seti olusturur: tedarikciler, tarifler, '
        'musteriler, uctan uca satin alma -> uretim -> satis zinciri.'
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write('Tedarikciler ve urunler...')
            businesses = self._create_businesses()
            products = self._create_products(businesses)

            self.stdout.write('Tarifler (BOM)...')
            recipes = self._create_recipes(products)

            self.stdout.write('Satin alma ve teslimat (kismi dahil)...')
            green_lots = self._create_purchases(businesses, products)

            self.stdout.write('Uretim (kavurma partileri)...')
            roasted_lots = self._create_production(recipes, green_lots)

            self.stdout.write('Musteriler ve satislar...')
            self._create_sales(roasted_lots)

            self.stdout.write('AI icin dokumanlar...')
            self._create_documents()

        self.stdout.write(self.style.SUCCESS('Demo veri seti basariyla olusturuldu.'))

    def _create_businesses(self):
        data = [
            ('Brazil Farms Co', Business.BusinessType.SUPPLIER, 'brazil@example.com'),
            ('Ethiopia Highlands Coop', Business.BusinessType.SUPPLIER, 'ethiopia@example.com'),
            ('Colombia Sierra Trading', Business.BusinessType.SUPPLIER, 'colombia@example.com'),
            # NOT: Kendi kavurma isletmemizi de bir Business kaydi olarak
            # tutuyoruz -- Product.business alani zorunlu oldugu icin,
            # kendi urettigimiz (kavrulmus) urunlerin de bir "sahibi" olmasi
            # lazim. Pragmatik bir cozum, ideal degil ama yeterli.
            ('Reflow Coffee Roastery', Business.BusinessType.SUPPLIER, 'roastery@example.com'),
        ]
        businesses = {}
        for name, btype, email in data:
            business, _ = Business.objects.get_or_create(
                name=name,
                defaults={
                    'business_type': btype,
                    'contact_email': email,
                    'contact_phone': '0000000000',
                },
            )
            businesses[name] = business
        return businesses

    def _create_products(self, businesses):
        data = [
            ('Brazil Santos Green', 'Green Coffee', businesses['Brazil Farms Co']),
            ('Ethiopia Yirgacheffe Green', 'Green Coffee', businesses['Ethiopia Highlands Coop']),
            ('Colombia Supremo Green', 'Green Coffee', businesses['Colombia Sierra Trading']),
            ('House Blend Roasted', 'Roasted Coffee', businesses['Reflow Coffee Roastery']),
            ('Single Origin Ethiopia Roasted', 'Roasted Coffee', businesses['Reflow Coffee Roastery']),
            ('Dark Roast Blend Roasted', 'Roasted Coffee', businesses['Reflow Coffee Roastery']),
        ]
        products = {}
        for name, category, business in data:
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'unit': Product.Unit.KILOGRAM,
                    'business': business,
                },
            )
            products[name] = product
        return products

    def _create_recipes(self, products):
        recipes = {}

        house_blend, _ = Recipe.objects.get_or_create(
            name='House Blend',
            defaults={'output_product': products['House Blend Roasted']},
        )
        RecipeComponent.objects.get_or_create(
            recipe=house_blend, input_product=products['Brazil Santos Green'],
            defaults={'ratio_percent': Decimal('70')},
        )
        RecipeComponent.objects.get_or_create(
            recipe=house_blend, input_product=products['Ethiopia Yirgacheffe Green'],
            defaults={'ratio_percent': Decimal('30')},
        )
        recipes['House Blend'] = house_blend

        single_origin, _ = Recipe.objects.get_or_create(
            name='Single Origin Ethiopia',
            defaults={'output_product': products['Single Origin Ethiopia Roasted']},
        )
        RecipeComponent.objects.get_or_create(
            recipe=single_origin, input_product=products['Ethiopia Yirgacheffe Green'],
            defaults={'ratio_percent': Decimal('100')},
        )
        recipes['Single Origin Ethiopia'] = single_origin

        # Ucuncu, uc bilesenli bir tarif -- BOM'un gercekten esnek oldugunu
        # gostermek icin bilerek daha karmasik kurduk.
        dark_roast, _ = Recipe.objects.get_or_create(
            name='Dark Roast Blend',
            defaults={'output_product': products['Dark Roast Blend Roasted']},
        )
        RecipeComponent.objects.get_or_create(
            recipe=dark_roast, input_product=products['Brazil Santos Green'],
            defaults={'ratio_percent': Decimal('50')},
        )
        RecipeComponent.objects.get_or_create(
            recipe=dark_roast, input_product=products['Colombia Supremo Green'],
            defaults={'ratio_percent': Decimal('30')},
        )
        RecipeComponent.objects.get_or_create(
            recipe=dark_roast, input_product=products['Ethiopia Yirgacheffe Green'],
            defaults={'ratio_percent': Decimal('20')},
        )
        recipes['Dark Roast Blend'] = dark_roast

        return recipes

    def _create_purchases(self, businesses, products):
        # Her calistirmada farkli lot kodlari uretmek icin saat/dakika/saniye
        # ekliyoruz -- bu script temiz bir veritabaninda BIR KEZ calistirilmak
        # uzere tasarlandi, art arda cok hizli calistirirsan (ayni saniyede)
        # lot kodu cakismasi olabilir.
        suffix = timezone.now().strftime('%H%M%S')
        far_expiry = timezone.localdate() + timedelta(days=180)

        po1 = PurchaseOrder.objects.create(supplier=businesses['Brazil Farms Co'], status='sent')
        item1 = PurchaseOrderItem.objects.create(
            purchase_order=po1, product=products['Brazil Santos Green'],
            quantity_ordered=Decimal('300'), unit_price=Decimal('42.00'),
        )
        # Bilerek KISMI teslimat: 180 + 120 = 300, iki ayri sevkiyat
        receive_goods(item1, Decimal('180'), f'BRZ-{suffix}-A', far_expiry)
        receipt1 = receive_goods(item1, Decimal('120'), f'BRZ-{suffix}-B', far_expiry)

        po2 = PurchaseOrder.objects.create(supplier=businesses['Ethiopia Highlands Coop'], status='sent')
        item2 = PurchaseOrderItem.objects.create(
            purchase_order=po2, product=products['Ethiopia Yirgacheffe Green'],
            quantity_ordered=Decimal('150'), unit_price=Decimal('65.00'),
        )
        receipt2 = receive_goods(item2, Decimal('150'), f'ETH-{suffix}', far_expiry)

        po3 = PurchaseOrder.objects.create(supplier=businesses['Colombia Sierra Trading'], status='sent')
        item3 = PurchaseOrderItem.objects.create(
            purchase_order=po3, product=products['Colombia Supremo Green'],
            quantity_ordered=Decimal('100'), unit_price=Decimal('55.00'),
        )
        receipt3 = receive_goods(item3, Decimal('100'), f'COL-{suffix}', far_expiry)

        return {
            'Brazil Santos Green': receipt1.lot,
            'Ethiopia Yirgacheffe Green': receipt2.lot,
            'Colombia Supremo Green': receipt3.lot,
        }

    def _create_production(self, recipes, green_lots):
        suffix = timezone.now().strftime('%H%M%S')
        fresh_expiry = timezone.localdate() + timedelta(days=14)

        batch1 = create_roast_batch(
            recipe=recipes['House Blend'],
            input_lots={
                green_lots['Brazil Santos Green'].product_id: green_lots['Brazil Santos Green'],
                green_lots['Ethiopia Yirgacheffe Green'].product_id: green_lots['Ethiopia Yirgacheffe Green'],
            },
            output_quantity=Decimal('50'),
            output_lot_code=f'HB-{suffix}',
            output_expiry_date=fresh_expiry,
        )

        batch2 = create_roast_batch(
            recipe=recipes['Single Origin Ethiopia'],
            input_lots={
                green_lots['Ethiopia Yirgacheffe Green'].product_id: green_lots['Ethiopia Yirgacheffe Green'],
            },
            output_quantity=Decimal('20'),
            output_lot_code=f'SOE-{suffix}',
            output_expiry_date=fresh_expiry,
        )

        batch3 = create_roast_batch(
            recipe=recipes['Dark Roast Blend'],
            input_lots={
                green_lots['Brazil Santos Green'].product_id: green_lots['Brazil Santos Green'],
                green_lots['Colombia Supremo Green'].product_id: green_lots['Colombia Supremo Green'],
                green_lots['Ethiopia Yirgacheffe Green'].product_id: green_lots['Ethiopia Yirgacheffe Green'],
            },
            output_quantity=Decimal('30'),
            output_lot_code=f'DRB-{suffix}',
            output_expiry_date=fresh_expiry,
        )

        return {
            'House Blend Roasted': batch1.output_lot,
            'Single Origin Ethiopia Roasted': batch2.output_lot,
            'Dark Roast Blend Roasted': batch3.output_lot,
        }

    def _create_sales(self, roasted_lots):
        customers_data = [
            ('Kahve Molasi Cafe', Customer.CustomerType.WHOLESALE, 'molasi@example.com'),
            ('Fincan Kahve Evi', Customer.CustomerType.WHOLESALE, 'fincan@example.com'),
            ('Sokak Kahvesi', Customer.CustomerType.WHOLESALE, 'sokak@example.com'),
            ('Ahmet Yilmaz', Customer.CustomerType.RETAIL, 'ahmet@example.com'),
            ('Elif Kaya', Customer.CustomerType.RETAIL, 'elif@example.com'),
        ]
        customers = {}
        for name, ctype, email in customers_data:
            customer, _ = Customer.objects.get_or_create(
                name=name, defaults={'customer_type': ctype, 'contact_email': email},
            )
            customers[name] = customer

        # (musteri, urun, miktar, birim fiyat)
        sales_plan = [
            ('Kahve Molasi Cafe', 'House Blend Roasted', Decimal('10'), Decimal('350')),
            ('Fincan Kahve Evi', 'House Blend Roasted', Decimal('8'), Decimal('345')),
            ('Sokak Kahvesi', 'Dark Roast Blend Roasted', Decimal('12'), Decimal('370')),
            ('Ahmet Yilmaz', 'Single Origin Ethiopia Roasted', Decimal('1'), Decimal('420')),
            ('Elif Kaya', 'House Blend Roasted', Decimal('2'), Decimal('400')),
        ]
        for customer_name, product_name, quantity, unit_price in sales_plan:
            lot = roasted_lots[product_name]
            order = Order.objects.create(customer=customers[customer_name])
            OrderItem.objects.create(
                order=order, product=lot.product, lot=lot,
                quantity=quantity, unit_price=unit_price,
            )
            fulfill_order(order)

    def _create_documents(self):
        docs = [
            (
                'Kavurma Prosedürü',
                Document.Source.PROCEDURE,
                'Kavurma makinesi her kullanim sonrasi temizlenmelidir. '
                'Ideal kavurma sicakligi 200-230C arasindadir. Kavurma '
                'sonrasi kahve en az 24 saat dinlendirilmeli, ambalajlama '
                'oncesi degazasyona birakilmalidir.',
            ),
            (
                'Tedarikçi Notu - Brazil Farms Co',
                Document.Source.SUPPLIER_NOTE,
                'Brazil Farms Co ile calisma 2024 yilinda basladi. '
                'Teslimatlar genelde zamaninda gelir, kalite tutarlidir. '
                'Yillik sozlesme kapsaminda minimum 1000 kg alim taahhudu '
                'vardir.',
            ),
            (
                'İade ve Değişim Politikası',
                Document.Source.GENERAL,
                'Toptan musteriler, teslim tarihinden itibaren 7 gun icinde '
                'kalite sorunu bildirebilir. Perakende musteriler icin '
                'acilmamis urunlerde 14 gun iade hakki vardir.',
            ),
        ]
        for title, source, content in docs:
            Document.objects.get_or_create(
                title=title, defaults={'source': source, 'content': content},
            )