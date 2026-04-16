
    # 🔴 Decide behavior based on reason
    if reason in ['damage', 'order']:
        # behave like deduct
        self.quantity = max(0, self.quantity - qty)
        change_type = InventoryLog.DEDUCT

    else:
        # default → add
        self.quantity += qty
        change_type = InventoryLog.ADD

    self.save(update_fields=['quantity', 'updated_at'])

    InventoryLog.objects.create(
        inventory=self,
        change_type=change_type,
        quantity_changed=qty,
        quantity_after=self.quantity,
        reason=reason,
        note=note,
        updated_by=updated_by,
    )