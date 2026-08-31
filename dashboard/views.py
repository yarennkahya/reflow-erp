from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages

from inventory.models import Lot, Warehouse
from inventory.services import get_freshness_status
from purchasing.models import PurchaseOrder
from production.models import RoastBatch
from sales.models import Customer, Order
from crm.models import Opportunity
from hr.models import Employee, LeaveRequest
from finance.services import get_profitability_report


def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard-home')
    return render(request, 'public/landing.html')


def chat_page_view(request):
    return render(request, 'ai_layer/chat.html')


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
            'open_orders': PurchaseOrder.objects.filter(
                status__in=['draft', 'sent', 'confirmed', 'partially_received']
            ).count(),
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
            'active_sales': Opportunity.objects.filter(status='active').count(),
            'won_sales': Opportunity.objects.filter(status='won').count(),
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


@login_required
def account_settings_view(request):
    password_form = PasswordChangeForm(request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'email':
            email = request.POST.get('email', '').strip()
            request.user.email = email
            request.user.save(update_fields=['email'])
            messages.success(request, 'E-posta güncellendi.')
        elif action == 'password':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Şifre başarıyla değiştirildi.')

    groups = list(request.user.groups.values_list('name', flat=True))
    return render(request, 'dashboard/account_settings.html', {
        'password_form': password_form,
        'groups': groups,
    })
