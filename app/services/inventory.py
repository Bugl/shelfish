from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import InventoryItem
from app.repositories.inventory import find_matching_inventory_item, add_inventory_item, delete_inventory_item


def set_quantity(
    item: InventoryItem,
    new_quantity: Decimal,
    db: Session,
) -> None:
    """
    Changes the amount of one single package from item to new quantity.

    If there are multiple packages, one package is extracted from item.
    This will either be added to a matching item or created as a new item.
    """
    _validate_quantity_change(item, new_quantity)

    #If quantity drops to 0, the package is removed.
    if new_quantity <= 0:
        new_package_count = item.package_count - 1
        set_package_count(item, new_package_count, db)
        return


    # Single Package: Item itself can be altered
    if item.package_count == 1:
        item.quantity_per_package = new_quantity
        return

    # Multiple packages: one package should be extracted
    matching_item = find_matching_inventory_item(db, item, new_quantity)

    remove_one_package(item, db)

    if matching_item:
        add_one_package(matching_item)
        return

    _create_single_package_item(db, item, new_quantity)

def set_package_count(
        item: InventoryItem,
        new_package_count: int,
        db: Session,
) -> None:
    if new_package_count <= 0:
        delete_inventory_item(db,item)
        return
    item.package_count = new_package_count

def remove_one_package(item: InventoryItem, db: Session) -> None:
    if item.package_count == 1:
        db.delete(item)
    else:
        item.package_count -= 1

def add_one_package(item: InventoryItem) -> None:
    item.package_count += 1

def _validate_quantity_change(item: InventoryItem, new_quantity: Decimal) -> None:
    if item.package_count < 1:
        raise ValidationError("An item must have at least one package")

    if not new_quantity.is_finite() or new_quantity <= Decimal("0"):
        raise ValidationError("quantity_per_package must be a finite Decimal greater than zero")

def _create_single_package_item(
        db: Session,
        source: InventoryItem,
        quantity_per_package: Decimal,
) -> InventoryItem:
    new_item = InventoryItem(
        product_id=source.product_id,
        container_id=source.container_id,
        unit_id=source.unit_id,
        package_count=1,
        quantity_per_package=quantity_per_package,
        frozen_on=source.frozen_on,
        note=source.note,
        best_before=source.best_before,
    )
    db.add(new_item)
    return new_item