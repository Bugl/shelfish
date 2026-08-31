from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI,Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.database import Base, SessionLocal, engine, get_db
from app.models import Container, InventoryItem, Product, Unit

from datetime import date

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

INITIAL_CONTAINERS = [
    {"name": "Kleiner Gefrierschrank"},
    {"name": "Großer Gefrierschrank"},
]

INITIAL_UNITS = [
    {"name": "Stück", "symbol": "Stk.", "sort_order": 10},
    {"name": "Gramm", "symbol": "g", "sort_order": 20},
    {"name": "Kilogramm", "symbol": "kg", "sort_order": 30},
    {"name": "Milliliter", "symbol": "ml", "sort_order": 40},
    {"name": "Liter", "symbol": "l", "sort_order": 50},
    {"name": "Packung", "symbol": "Pkg.", "sort_order": 60},
    {"name": "Portion", "symbol": "Port.", "sort_order": 70},
]


def seed_initial_data() -> None:
    with SessionLocal() as db:
        for container_data in INITIAL_CONTAINERS:
            existing_container = db.scalar(
                select(Container).where(
                    Container.name == container_data["name"],
                )
            )
            if existing_container is None:
                db.add(Container(**container_data))

        for unit_data in INITIAL_UNITS:
            existing_unit = db.scalar(
                select(Unit).where(Unit.name == unit_data["name"])
            )
            if existing_unit is None:
                db.add(Unit(**unit_data))

        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    seed_initial_data()
    yield


app = FastAPI(
    title="Shelfish",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def overview_root():
    return RedirectResponse("/container/1", status_code=303)

@app.get("/container/{container_id}/new")
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

@app.get("/container/{container_id}")
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

@app.post("/container/{container_id}/new")
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

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
