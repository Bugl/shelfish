from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import InventoryItem
from app.repositories.inventory import find_matching_inventory_item, add_inventory_item


def move_one_package_to_quantity(
    item: InventoryItem,
    new_quantity: Decimal,
    db: Session,
) -> None:
    matching_item = find_matching_inventory_item(db, item, new_quantity)

    if item.package_count == 1:
        if matching_item is not None:
            matching_item.package_count += 1
            db.delete(item)
        else:
            item.quantity_per_package = new_quantity
        return

    item.package_count -= 1

    if matching_item is not None:
        matching_item.package_count += 1
        return
    add_inventory_item(
        db=db,
        product_id=item.product_id,
        container_id=item.container_id,
        unit_id=item.unit_id,
        package_count=1,
        quantity_per_package=new_quantity,
        frozen_on=item.frozen_on,
        best_before=item.best_before,
        note=item.note,
    )

