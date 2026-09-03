from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Container, InventoryItem, Product, Unit
from app.services.inventory import move_one_package_to_quantity
from app.templates import templates

from app.repositories.inventory import get_inventory_item, add_inventory_item

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

    add_inventory_item(
        db=db,
        product_id=product.id,
        container_id=active_container.id,
        unit_id=unit.id,
        package_count=package_count,
        quantity_per_package=quantity_per_package,
        frozen_on=frozen_on,
        best_before=best_before,
        note=note.strip() if note else None,
    )
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
    item = get_inventory_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
    container_id = item.container_id

    delete_inventory_item(item_id, db)
    db.commit()

    return RedirectResponse(
        url=f"/container/{container_id}",
        status_code=303,
    )

@router.post("/inventory-item/{item_id}/package/increase")
def increase_package_count(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = get_inventory_item(db, item_id)
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
    item = get_inventory_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
    container_id = item.container_id
    item.package_count -= 1
    if item.package_count <= 0:
        delete_inventory_item(item_id, db)
    db.commit()

    return RedirectResponse(
        url=f"/container/{container_id}",
        status_code=303,
    )

@router.post("/inventory-items/{item_id}/quantity/increase")
def increase_quantity_per_package(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = get_inventory_item(db, item_id)

    if item is None:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")

    container_id = item.container_id

    move_one_package_to_quantity(
        item=item,
        new_quantity=item.quantity_per_package + Decimal("1"),
        db=db,
    )

    db.commit()

    return RedirectResponse(
        url=f"/container/{container_id}",
        status_code=303,
    )

@router.post("/inventory-items/{item_id}/quantity/decrease")
def decrease_quantity_per_package(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = get_inventory_item(db, item_id)

    if item is None:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")

    move_one_package_to_quantity(
        item=item,
        new_quantity=item.quantity_per_package - Decimal("1"),
        db=db,
    )

    db.commit()

    return RedirectResponse(
        url=f"/container/{item.container_id}",
        status_code=303,
    )

@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

