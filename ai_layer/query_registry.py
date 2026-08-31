QUERY_REGISTRY = {
    'inventory_products': {
        'model': 'inventory.Product',
        'filterable_fields': ['name__icontains', 'category', 'business__name__icontains'],
        'display_fields': ['name', 'category', 'unit', 'business__name'],
    },
    'inventory_lots': {
        'model': 'inventory.Lot',
        'filterable_fields': ['product__name__icontains', 'warehouse__name', 'expiry_date__lte', 'expiry_date__gte'],
        'display_fields': ['lot_code', 'product__name', 'expiry_date', 'warehouse__name'],
    },
    'purchasing_orders': {
        'model': 'purchasing.PurchaseOrder',
        'filterable_fields': ['status', 'supplier__name__icontains'],
        'display_fields': ['id', 'supplier__name', 'status', 'created_at'],
    },
    'production_batches': {
        'model': 'production.RoastBatch',
        'filterable_fields': ['recipe__name__icontains'],
        'display_fields': ['recipe__name', 'output_lot__lot_code', 'total_output_quantity', 'roasted_at'],
    },
    'sales_orders': {
        'model': 'sales.Order',
        'filterable_fields': ['status', 'customer__name__icontains'],
        'display_fields': ['id', 'customer__name', 'status', 'created_at'],
    },
    'sales_customers': {
        'model': 'sales.Customer',
        'filterable_fields': ['customer_type', 'name__icontains'],
        'display_fields': ['name', 'customer_type', 'contact_email'],
    },
    'sales_returns': {
        'model': 'sales.ReturnRequest',
        'filterable_fields': ['status', 'reason'],
        'display_fields': ['id', 'order_item__product__name', 'reason', 'status', 'requested_at'],
    },
    'crm_opportunities': {
        'model': 'crm.Opportunity',
        'filterable_fields': ['stage', 'customer__name__icontains'],
        'display_fields': ['title', 'customer__name', 'stage', 'estimated_value'],
    },
    'finance_invoices': {
        'model': 'finance.Invoice',
        'filterable_fields': ['status', 'order__customer__name__icontains'],
        'display_fields': ['id', 'order__customer__name', 'status', 'issued_at'],
    },
    'hr_employees': {
        'model': 'hr.Employee',
        'filterable_fields': ['employment_status', 'department__name', 'name__icontains'],
        'display_fields': ['name', 'department__name', 'position__title', 'employment_status'],
    },
    'hr_leave_requests': {
        'model': 'hr.LeaveRequest',
        'filterable_fields': ['status', 'employee__name__icontains'],
        'display_fields': ['employee__name', 'leave_type__name', 'status', 'start_date', 'end_date'],
    },
    'meetings': {
        'model': 'meetings.Meeting',
        'filterable_fields': ['status', 'organizer__name__icontains'],
        'display_fields': ['title', 'organizer__name', 'start_time', 'status'],
    },
}
