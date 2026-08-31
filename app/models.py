from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
	Boolean,
	CheckConstraint,
	Date,
	DateTime,
	ForeignKey,
	Integer,
	Numeric,
	String,
	Text,
	UniqueConstraint,
	func,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Container(Base):
    __tablename__ = "containers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    inventory_items: Mapped[list[InventoryItem]] = relationship(
        back_populates="container",
    )


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    inventory_items: Mapped[list[InventoryItem]] = relationship(
        back_populates="unit",
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    inventory_items: Mapped[list[InventoryItem]] = relationship(
        back_populates="product",
    )


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        CheckConstraint("package_count >= 1", name="ck_inventory_package_count"),
        CheckConstraint(
            "quantity_per_package > 0",
            name="ck_inventory_quantity_per_package",
        ),
        UniqueConstraint(
            "container_id",
            "product_id",
            "unit_id",
            "quantity_per_package",
            "frozen_on",
            "best_before",
            "note",
            name="uq_inventory_item_batch",
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    container_id: Mapped[int] = mapped_column(
        ForeignKey("containers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=False,
    )

    package_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    quantity_per_package: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    frozen_on: Mapped[date] = mapped_column(Date, nullable=False)
    best_before: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    product: Mapped[Product] = relationship(back_populates="inventory_items")
    container: Mapped[Container] = relationship(back_populates="inventory_items")
    unit: Mapped[Unit] = relationship(back_populates="inventory_items")
