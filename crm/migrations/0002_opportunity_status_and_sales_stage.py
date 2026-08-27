# Generated manually for the CRM sales-management flow.

import django.db.models.deletion
from django.db import migrations, models


def set_existing_sale_statuses(apps, schema_editor):
    Opportunity = apps.get_model('crm', 'Opportunity')
    Opportunity.objects.filter(stage='won').update(status='won')
    Opportunity.objects.filter(stage='lost').update(status='lost')


def reset_existing_sale_statuses(apps, schema_editor):
    Opportunity = apps.get_model('crm', 'Opportunity')
    Opportunity.objects.update(status='active')


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0002_customer_is_active'),
        ('crm', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='opportunity',
            name='status',
            field=models.CharField(
                choices=[
                    ('active', 'Aktif'),
                    ('passive', 'Pasif'),
                    ('won', 'Kazanıldı'),
                    ('lost', 'Kaybedildi'),
                ],
                default='active',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='opportunity',
            name='customer',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='opportunities',
                to='sales.customer',
            ),
        ),
        migrations.AlterField(
            model_name='opportunity',
            name='stage',
            field=models.CharField(
                choices=[
                    ('new', 'İlk temas'),
                    ('in_discussion', 'İhtiyaç analizi'),
                    ('proposal_sent', 'Teklif sunuldu'),
                    ('negotiation', 'Pazarlık'),
                    ('won', 'Kazanıldı'),
                    ('lost', 'Kaybedildi'),
                ],
                default='new',
                max_length=20,
            ),
        ),
        migrations.RunPython(set_existing_sale_statuses, reset_existing_sale_statuses),
    ]
