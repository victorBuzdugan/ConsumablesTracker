"""Database SQLAlchemy class models"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import ForeignKey, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (DeclarativeBase, Mapped, MappedAsDataclass,
                            Session, declared_attr, mapped_column,
                            relationship, sessionmaker)
from werkzeug.security import check_password_hash, generate_password_hash

# factory for creating new database connections objects
engine = create_engine("sqlite:///inventory.db", echo=True)

# factory for Session objects
Session = sessionmaker(bind=engine)


class Base(MappedAsDataclass, DeclarativeBase):
    """Base class for SQLAlchemy Declarative Mapping"""
    
    # set table name
    @declared_attr.directive
    def __tablename__(cls):
        if cls.__name__ == "Category":
            return "categories"
        return (cls.__name__.lower() + "s")
    
    # id and name for all tables
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)


class User(Base):
    """User database table mapping.

    :param id: user id
    :param name: user name
    :param password: user password
    :param products: user's assigned for inventorying list of products
    :param admin: user has administrator rights
    :param in_use: user can still be used; not obsolete
    :param done_inv: user has sent the inventory
    :param details: user details, extra info
    """
    password: Mapped[str] = mapped_column(repr=False)
    products: Mapped[List["Product"]] = relationship(
        default_factory=list, back_populates="responsable", repr=False)
    admin: Mapped[bool] = mapped_column(default=False)
    in_use: Mapped[bool] = mapped_column(default=True)
    done_inv: Mapped[bool] = mapped_column(default=True)
    details: Mapped[Optional[str]] = mapped_column(default=None, repr=False)


class Category(Base):
    """Categories database table mapping.
    
    :param id: category id
    :param name: category name
    :param products: list of products belonging to this category
    :param in_use: category can still be used; not obsolete
    :param description: category description, extra info
    """
    products: Mapped[List["Product"]] = relationship(
        default_factory=list, back_populates="category", repr=False)
    in_use: Mapped[bool] = mapped_column(default=True)
    description: Mapped[Optional[str]] = mapped_column(
        default=None, repr=False)



class Supplier(Base):
    """Suppliers database table mapping.
    
    :param id: supplier id
    :param name: supplier name
    :param products: list of products belonging to this supplier
    :param in_use: supplier can still be used; not obsolete
    :param details: supplier details, extra info
    """
    products: Mapped[List["Product"]] = relationship(
        default_factory=list, back_populates="supplier", repr=False)
    in_use: Mapped[bool] = mapped_column(default=True)
    details: Mapped[Optional[str]] = mapped_column(
        default=None, repr=False)



class Product(Base):
    """Products database table mapping.

    :param id: product id
    :param name: product short name / number / code
    :param description: produc description, extra info
    :param responsable_id: user id responsable for inventorying the product
    :param responsable: `User` class object for responsable
    :param category_id: category id of this product
    :param category: `Category` class object of this product
    :param supplier_id: supplier id of this product
    :param supplier: `Supplier` class object of this product
    :param meas_unit: measuring unit
    :param min_stock: minimum stock
    :param ord_qty: order quantity
    :param to_order: product needs to be ordered
    If `responsable` sees that shelf quantity is less than `min_stock` checks
    in the app triggering `to_order = True`. The admin will see that
    he needs to order `ord_qty` of this product.
    :param critical: product is a critical product
    :param in_use: product is not obsolete
    """
    description: Mapped[str]
    responsable_id = mapped_column(ForeignKey("users.id"), nullable=False)
    responsable: Mapped[User] = relationship(back_populates="products",
                                             repr=False)
    category_id = mapped_column(ForeignKey("categories.id"), nullable=False)
    category: Mapped[Category] = relationship(back_populates="products",
                                              repr=False)
    supplier_id = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    supplier: Mapped[Supplier] = relationship(back_populates="products",
                                              repr=False)
    meas_unit: Mapped[str]
    min_stock: Mapped[int]
    ord_qty: Mapped[int]
    to_order: Mapped[bool] = mapped_column(default=False)
    critical: Mapped[bool] = mapped_column(default=False)
    in_use: Mapped[bool] = mapped_column(default=True)


if __name__ == "__main__":

    # with Session() as session:
    #     items = session.scalars(select(User)).all()
    #     for item in items:
    #         print(item.id, item.name)
    #     pass

    pass
