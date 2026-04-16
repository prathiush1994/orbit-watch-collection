from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator

from .models import Inventory, InventoryLog
from store.models import ProductVariant


# ─────────────────────────────────────────────────────────────────────────────
# Helper: ensure every ProductVariant has an Inventory row
# ─────────────────────────────────────────────────────────────────────────────

def _sync_inventories():
    """Create missing Inventory rows for any variant that doesn't have one yet."""
    for variant in ProductVariant.objects.select_related('inventory').all():
        inv, created = Inventory.objects.get_or_create(variant=variant)
        if created:
            # Bootstrap quantity from the legacy stock field (one-time migration)
            if variant.stock and variant.stock > 0:
                inv.quantity = variant.stock
                inv.save(update_fields=['quantity'])


# ─────────────────────────────────────────────────────────────────────────────
# List view — all inventory rows
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='admin_login')
def inventory_list(request):
    _sync_inventories()

    q = request.GET.get('q', '').strip()
    filter_stock = request.GET.get('stock', '')   # 'low' | 'out' | ''

    inventories = (
        Inventory.objects
        .select_related('variant', 'variant__product', 'variant__product__brand')
        .order_by('variant__product__product_name', 'variant__color_name')
    )

    if q:
        inventories = inventories.filter(
            Q(variant__product__product_name__icontains=q) |
            Q(variant__color_name__icontains=q) |
            Q(variant__product__brand__brand_name__icontains=q)
        )

    if filter_stock == 'low':
        # quantity > 0 and quantity <= threshold — approximate (threshold=5 default)
        inventories = inventories.filter(quantity__gt=0, quantity__lte=5)
    elif filter_stock == 'out':
        inventories = inventories.filter(quantity__lte=0)

    # Summary counts
    all_inv     = Inventory.objects.all()
    total_items = all_inv.count()
    out_of_stock = all_inv.filter(quantity__lte=0).count()
    low_stock    = all_inv.filter(quantity__gt=0, quantity__lte=5).count()

    paginator = Paginator(inventories, 20)
    page      = request.GET.get('page', 1)
    page_obj  = paginator.get_page(page)

    return render(request, 'adminpanel/inventory_list.html', {
        'active':       'inventory',
        'inventories':  page_obj,
        'search_query': q,
        'filter_stock': filter_stock,
        'total_items':  total_items,
        'out_of_stock': out_of_stock,
        'low_stock':    low_stock,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Add stock view — for a specific variant
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='admin_login')
def inventory_add_stock(request, inventory_id):
    inventory = get_object_or_404(
        Inventory.objects.select_related(
            'variant', 'variant__product'
        )
        .prefetch_related('variant__images'),
        pk=inventory_id
    )

    # Recent log for this item (last 15)
    logs = inventory.logs.select_related('updated_by').order_by('-created_at')[:15]

    if request.method == 'POST':
        try:
            qty    = int(request.POST.get('quantity', 0))
            reason = request.POST.get('reason', 'restock')
            note   = request.POST.get('note', '').strip()
        except (ValueError, TypeError):
            messages.error(request, "Invalid quantity entered.")
            return redirect('admin_inventory_add_stock', inventory_id=inventory_id)

        if qty <= 0:
            messages.error(request, "Quantity must be greater than zero.")
            return redirect('admin_inventory_add_stock', inventory_id=inventory_id)

        inventory.add_stock(
            qty=qty,
            reason=reason,
            updated_by=request.user,
            note=note,
        )

        variant_name = str(inventory.variant)
        messages.success(
            request,
            f"Added {qty} unit{'s' if qty != 1 else ''} to {variant_name}. "
            f"New stock: {inventory.quantity}."
        )
        return redirect('admin_inventory_list')

    return render(request, 'adminpanel/inventory_add_stock.html', {
        'active':    'inventory',
        'inventory': inventory,
        'logs':      logs,
        'reason_choices': InventoryLog.REASON_CHOICES,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Log view — full history for one variant
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='admin_login')
def inventory_log(request, inventory_id):
    inventory = get_object_or_404(
        Inventory.objects.select_related('variant', 'variant__product'),
        pk=inventory_id
    )

    logs = inventory.logs.select_related('updated_by').order_by('-created_at')
    paginator = Paginator(logs, 20)
    page      = request.GET.get('page', 1)
    page_obj  = paginator.get_page(page)

    return render(request, 'adminpanel/inventory_log.html', {
        'active':    'inventory',
        'inventory': inventory,
        'logs':      page_obj,
    })