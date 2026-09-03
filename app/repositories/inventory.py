from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InventoryItem


def get_inventory_item(
    db: Session,
    item_id: int,
) -> InventoryItem | None:
    return db.get(InventoryItem, item_id)

def find_matching_inventory_item(
    db: Session,
    item: InventoryItem,
    quantity_per_package: Decimal,
) -> InventoryItem | None:
    return db.scalar(
        select(InventoryItem).where(
            InventoryItem.id != item.id,
            InventoryItem.container_id == item.container_id,
            InventoryItem.product_id == item.product_id,
            InventoryItem.unit_id == item.unit_id,
            InventoryItem.quantity_per_package == quantity_per_package,
            InventoryItem.frozen_on == item.frozen_on,
            InventoryItem.best_before == item.best_before,
            InventoryItem.note == item.note,
        )
    )

def add_inventory_item(
    db: Session,
    product_id: int,
    container_id: int,
    unit_id: int,
    package_count: int,
    quantity_per_package: Decimal,
    frozen_on,
    best_before,
    note: str | None,
) -> InventoryItem:
    item = InventoryItem(
        product_id=product_id,
        container_id=container_id,
        unit_id=unit_id,
        package_count=package_count,
        quantity_per_package=quantity_per_package,
        frozen_on=frozen_on,
        best_before=best_before,
        note=note,
    )

    db.add(item)

    return item


def delete_inventory_item(
    db: Session,
    item: InventoryItem,
) -> None:
    db.delete(item)