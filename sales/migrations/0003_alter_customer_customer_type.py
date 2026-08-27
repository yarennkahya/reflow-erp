# Generated manually to keep the customer type labels in sync with the CRM UI.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0002_customer_is_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='customer_type',
            field=models.CharField(
                choices=[
                    ('wholesale', 'Toptan (kafe)'),
                    ('retail', 'Perakende (bireysel)'),
                ],
                max_length=20,
            ),
        ),
    ]
