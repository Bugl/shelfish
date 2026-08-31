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
from app.routers.inventory import router as inventory_router

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

app.include_router(inventory_router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")



