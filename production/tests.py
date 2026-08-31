from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from inventory.models import Business, Lot, Product

from .models import Recipe, RecipeComponent, RoastBatch


class RoastBatchCreateViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='production-user', password='secret123'
        )
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label__in=('production', 'inventory')
        ))
        self.business = Business.objects.create(
            name='Production Test Business',
            business_type=Business.BusinessType.INTERNAL,
            contact_email='production@example.com',
            contact_phone='+90 555 000 00 00',
        )
        self.input_product = Product.objects.create(
            name='Production Test Green Coffee',
            category='Yeşil kahve',
            unit=Product.Unit.KILOGRAM,
            business=self.business,
        )
        output_product = Product.objects.create(
            name='Production Test Roasted Coffee',
            category='Kavrulmuş kahve',
            unit=Product.Unit.KILOGRAM,
            business=self.business,
        )
        self.input_lot = Lot.objects.create(
            product=self.input_product,
            lot_code='PROD-INPUT-001',
            expiry_date=timezone.localdate() + timedelta(days=90),
            quantity_received=Decimal('20.000'),
            unit_cost=Decimal('50.00'),
        )
        self.recipe = Recipe.objects.create(
            name='Production Test Recipe', output_product=output_product
        )
        RecipeComponent.objects.create(
            recipe=self.recipe,
            input_product=self.input_product,
            ratio_percent=Decimal('100.00'),
        )
        self.client.force_login(self.user)

    def test_selected_recipe_creates_batch_from_its_available_lot(self):
        response = self.client.get(
            reverse('production-batch-create'), {'recipe': self.recipe.pk}
        )
        self.assertContains(response, 'PROD-INPUT-001')

        response = self.client.post(reverse('production-batch-create'), {
            'recipe': self.recipe.pk,
            f'lot_{self.input_product.pk}': self.input_lot.pk,
            'output_quantity': '10.000',
            'output_lot_code': 'PROD-OUTPUT-001',
            'output_expiry_date': (
                timezone.localdate() + timedelta(days=30)
            ).isoformat(),
        })

        batch = RoastBatch.objects.get()
        self.assertRedirects(
            response, reverse('production-batch-detail', args=[batch.pk])
        )
        self.assertEqual(batch.output_lot.lot_code, 'PROD-OUTPUT-001')
