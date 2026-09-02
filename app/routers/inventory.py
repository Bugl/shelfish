from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Container, InventoryItem, Product, Unit
from app.templates import templates

router = APIRouter()

@router.get("/")
def overview_root():
    return RedirectResponse("/container/1", status_code=303)

@router.get("/container/{container_id}/new")
def new_inventory_item_form(
    container_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    active_container = db.get(Container, container_id)
    if active_container is None:
        raise HTTPException(status_code=404, detail="Behälter nicht gefunden")

    units = db.scalars(
        select(Unit).order_by(Unit.sort_order)
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="inventory_item_form.html",
        context={
            "active_container": active_container,
            "units": units,
        },
    )

@router.get("/container/{container_id}")
def overview(
    container_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    containers = db.scalars(
        select(Container).order_by(Container.id)
    ).all()

    active_container = db.get(Container, container_id)
    if active_container is None:
        raise HTTPException(status_code=404, detail="Behälter nicht gefunden")

    inventory_items = db.scalars(
        select(InventoryItem)
        .where(InventoryItem.container_id == container_id)
        .order_by(InventoryItem.frozen_on.asc().nulls_last())
    ).all()

    active_index = next(
        index
        for index, container in enumerate(containers)
        if container.id == active_container.id
    )

    previous_container = containers[(active_index - 1) % len(containers)]
    next_container = containers[(active_index +1) % len(containers)]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "containers": containers,
            "active_container": active_container,
            "inventory_items": inventory_items,
            "previous_container": previous_container,
            "next_container": next_container,
        },
    )

@router.post("/container/{container_id}/new")
def create_inventory_item(
    container_id: int,
    product_name: str = Form(...),
    package_count: int = Form(...),
    quantity_per_package: float = Form(...),
    unit_id: int = Form(...),
    frozen_on: date = Form(...),
    best_before: date | None = Form(None),
    note: str | None = Form(None),
    db: Session = Depends(get_db),
):
    active_container = db.get(Container, container_id)
    if active_container is None:
        raise HTTPException(status_code=404, detail="Behälter nicht gefunden")

    unit = db.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Einheit nicht gefunden")

    product = db.scalar(
        select(Product).where(Product.name == product_name.strip())
    )

    if product is None:
        product = Product(name=product_name.strip())
        db.add(product)
        db.flush()

    inventory_item = InventoryItem(
        product_id=product.id,
        container_id=active_container.id,
        unit_id=unit.id,
        package_count=package_count,
        quantity_per_package=quantity_per_package,
        frozen_on=frozen_on,
        best_before=best_before,
        note=note.strip() if note else None,
    )

    db.add(inventory_item)
    db.commit()

    return RedirectResponse(
        url=f"/container/{active_container.id}",
        status_code=303,
    )

@router.post("/inventory-item/{item_id}/delete")
def delete_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")

    db.delete(item)
    db.commit()

    return RedirectResponse(
        url=f"/container/{item.container_id}",
        status_code=303,
    )

@router.post("/inventory-item/{item_id}/package/increase")
def increase_package_count(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")

    item.package_count += 1
    db.commit()

    return RedirectResponse(
        url=f"/container/{item.container_id}",
        status_code=303,
    )

@router.post("/inventory-item/{item_id}/package/decrease")
def decrease_package_count(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")

    item.package_count -= 1
    if item.package_count <= 0:
        db.delete(item)

    db.commit()

    return RedirectResponse(
        url=f"/container/{item.container_id}",
        status_code=303,
    )

@router.post("/inventory-items/{item_id}/quantity/increase")
def increase_quantity(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")

@router.post("/inventory-items/{item_id}/quantity/decrease")
def decrease_quantity(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Eintra gefunden")

    container_id = item.container_id
    new_quantity = item.quantity_per_package + 1

    if item.quantity_per_package == 1:
        if item.package_count == 1:
            db.delete(item)
        else:
            item.package_count -= 1

        db.commit()

        return RedirectResponse(
            url=f"/container/{container_id}",
            status_code=303,
        )

    new_quantity = item.quantity_per_package - 1

    matching_item = db.scalar(
        select(InventoryItem).where(
            InventoryItem.id != item.id,
            InventoryItem.container_id == item.container_id,
            InventoryItem.product_id == item.product_id,
            InventoryItem.unit_id == item.unit_id,
            InventoryItem.quantity_per_package == new_quantity,
            InventoryItem.frozen_on == item.frozen_on,
            InventoryItem.best_before == item.best_before,
            InventoryItem.note == item.note,
        )
    )

    if item.package_count == 1:
        if matching_item is not None:
            matching_item.package_count += 1
            db.delete(item)
        else:
            item.quantity_per_package = new_quantity
    else:
        item.package_count -= 1

        if matching_item is not None:
            matching_item.package_count += 1
        else:
            db.add(
                InventoryItem(
                    product_id=item.product_id,
                    container_id=item.container_id,
                    unit_id=item.unit_id,
                    package_count=1,
                    quantity_per_package=new_quantity,
                    frozen_on=item.frozen_on,
                    best_before=item.best_before,
                    note=item.note,
                )
            )

    db.commit()

    return RedirectResponse(
        url=f"/container/{container_id}",
        status_code=303,
    )

@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

