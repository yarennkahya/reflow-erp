from django.shortcuts import render

from inventory.models import Lot, Warehouse
from inventory.services import get_freshness_status
from purchasing.models import PurchaseOrder
from production.models import RoastBatch
from sales.models import Customer, Order
from crm.models import Opportunity
from hr.models import Employee, LeaveRequest
from finance.services import get_profitability_report


def dashboard_view(request):
    profitability = get_profitability_report()

    context = {
        'inventory': {
            'total_lots': Lot.objects.count(),
            'warehouses': Warehouse.objects.count(),
            'critical_lots': sum(
                1 for lot in Lot.objects.all()
                if get_freshness_status(lot) in ('PRIORITY_SALE', 'WASTE')
            ),
        },
        'purchasing': {
            'total_orders': PurchaseOrder.objects.count(),
            'open_orders': PurchaseOrder.objects.exclude(status='received').count(),
        },
        'production': {
            'total_batches': RoastBatch.objects.count(),
        },
        'sales': {
            'total_customers': Customer.objects.count(),
            'fulfilled_orders': Order.objects.filter(status='fulfilled').count(),
            'total_revenue': profitability['total_revenue'],
        },
        'crm': {
            'open_opportunities': Opportunity.objects.exclude(stage__in=['won', 'lost']).count(),
            'won_opportunities': Opportunity.objects.filter(stage='won').count(),
        },
        'hr': {
            'total_employees': Employee.objects.count(),
            'pending_leaves': LeaveRequest.objects.filter(status='pending').count(),
        },
        'finance': {
            'total_profit': profitability['total_profit'],
            'margin_percent': profitability['margin_percent'],
        },
    }

    return render(request, 'dashboard/home.html', context)