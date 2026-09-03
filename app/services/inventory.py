from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import InventoryItem
from app.repositories.inventory import find_matching_inventory_item, add_inventory_item, delete_inventory_item


def set_quantity(
    item: InventoryItem,
    new_quantity: Decimal,
    db: Session,
) -> None:
    #If quantity drops to 0, the package is removed.
    if new_quantity <= 0:
        new_package_count = item.package_count - 1
        set_package_count(item, new_package_count, db)

    # If An item with matching quantity is found, increase its package count while decreasing the package count of the original item.
    matching_item = find_matching_inventory_item(db, item, new_quantity)

    if matching_item is not None:
        set_package_count(matching_item, matching_item.package_count + 1, db)
        set_package_count(item, item.package_count - 1, db)
        return

    # Else clone item with package count set to 1 and new quantity.
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

def set_package_count(
        item: InventoryItem,
        new_package_count: int,
        db: Session,
) -> None:
    if new_package_count <= 0:
        delete_inventory_item(db,item)
        return
    item.package_count = new_package_count
