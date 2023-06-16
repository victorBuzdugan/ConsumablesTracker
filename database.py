"""Database SQLAlchemy class models"""

from typing import List, Optional

from sqlalchemy import ForeignKey, Text, create_engine, select
from sqlalchemy.orm import (DeclarativeBase, Mapped, Session, mapped_column,
                            sessionmaker, relationship, MappedAsDataclass)

# factory for creating new database connections objects
engine = create_engine("sqlite:///inventory.db", echo=True)

# factory for Session objects
Session = sessionmaker(bind=engine)

class Base(MappedAsDataclass, DeclarativeBase):
    """Base class for SQLAlchemy Declarative Mapping"""
    pass

class User(Base):
    """User database table mapping.
    
    :param admin: user has administrator rights
    :param in_use: user can still be used
    :param done_inv: user has sent the inventory
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column(repr=False)
    products: Mapped[List["Product"]] = relationship(
        default_factory=list, back_populates="responsable")
    admin: Mapped[bool] = mapped_column(default=False)
    in_use: Mapped[bool] = mapped_column(default=True)
    done_inv: Mapped[bool] = mapped_column(default=True)
    details: Mapped[Optional[str]] = mapped_column(default=None, repr=False)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    products: Mapped[List["Product"]] = relationship(
        default_factory=list, back_populates="category")
    in_use: Mapped[bool] = mapped_column(default=True)
    description: Mapped[Optional[str]] = mapped_column(
        default=None, repr=False)


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    products: Mapped[List["Product"]] = relationship(
        default_factory=list, back_populates="supplier")
    in_use: Mapped[bool] = mapped_column(default=True)
    details: Mapped[Optional[str]] = mapped_column(
        default=None, repr=False)


class Product(Base):
    """Products database table mapping.
    
    :param name: product short name / number / code.
    :param responsable: user responsable for inventorying the product.
    :param meas_unit: measuring unit.
    :param min_stock: minimum stock.
    :param ord_qty: order quantity.
    If `responsable` sees that shelf quantity is less than `min_stock` checks
    in the app triggering `to_order = True`. The admin will see that
    he needs to order `ord_qty` of this product.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    responsable_id = mapped_column(ForeignKey("users.id"))
    responsable: Mapped[User] = relationship(back_populates="products")
    category_id = mapped_column(ForeignKey("categories.id"))
    category: Mapped[Category] = relationship(back_populates="products")
    supplier_id = mapped_column(ForeignKey("suppliers.id"))
    supplier: Mapped[Supplier] = relationship(back_populates="products")
    meas_unit: Mapped[str]
    min_stock: Mapped[int]
    ord_qty: Mapped[int]
    to_order: Mapped[bool] = mapped_column(default=False)
    critical: Mapped[bool] = mapped_column(default=False)
    in_use: Mapped[bool] = mapped_column(default=True)
    
    # def __repr__(self) -> str:
    #     return (
    #         f"Product{{id={self.id}, name={self.name}, "
    #         f"category={self.category_id!r}, supplier={self.supplier_id}, "
    #         f"measuring_unit={self.meas_unit}, "
    #         f"minimum_stock={self.min_stock}, order_quantity{self.ord_qnt}, "
    #         f"need_to_order={self.to_order}, critical={self.critical}}}")

if __name__ == "__main__":

    with Session() as session:
        # suppliers = session.scalars(select(Supplier)).all()
        # for supplier in suppliers:
        #     print(supplier)
        # category = Supplier("Carrefour")
        # session.add(category)
        # session.commit()
        pass

