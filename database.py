"""Database SQLAlchemy class models"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import ForeignKey, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (DeclarativeBase, Mapped, MappedAsDataclass,
                            Session, declared_attr, mapped_column,
                            relationship, sessionmaker, validates, synonym)
from werkzeug.security import check_password_hash, generate_password_hash

# factory for creating new database connections objects
engine = create_engine("sqlite:///inventory.db", echo=True)

# factory for Session objects
dbSession = sessionmaker(bind=engine)


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
    :param password: hashed user password
    :param products: user's assigned for inventorying list of products
    :param admin: user has administrator rights
    :param in_use: user can still be used; not obsolete
    :param done_inv: user has sent the inventory
    :param reg_req: user has requested registration
    :param req_inv: user has requested inventorying
    :param details: user details, extra info
    """
    password: Mapped[str] = mapped_column(repr=False)
    products: Mapped[List["Product"]] = relationship(
        default_factory=list, back_populates="responsable", repr=False)
    admin: Mapped[bool] = mapped_column(default=False)
    in_use: Mapped[bool] = mapped_column(default=True)
    done_inv: Mapped[bool] = mapped_column(default=True)
    reg_req: Mapped[bool] = mapped_column(default=True)
    req_inv: Mapped[bool] = mapped_column(default=False)
    details: Mapped[Optional[str]] = mapped_column(default=None, repr=False)

    username = synonym("name")

    @property
    def inv_status(self) -> str:
        """Check user's inventory status."""
        if self.done_inv:
            return "sent"
        return "not sent"

    @validates("products")
    def validate_products(self,
                          key: Optional[list[Product]],
                          value: Product
                          ) -> Optional[Product]:
        """A user that's not in use or has a pending registration
        can't have products assigned."""
        if value and not self.in_use:
            raise ValueError(
                "'retired' users can't have products attached")
        if value and self.reg_req:
            raise ValueError(
                "user with pending registration can't have products attached")
        return value

    @validates("admin")
    def validate_admin(self, key: bool, value: bool
                       ) -> Optional[bool]:
        """A user that requested registration can't be admin."""
        if value and self.reg_req:
            raise ValueError("user with pending registration can't be admin")
        return value
    
    @validates("in_use")
    def validate_in_use(self, key: bool, value: bool
                        ) -> Optional[bool]:
        """A user that is 'responsible' for some products can't 'retire'.
        Set properties if user is not in use anymore."""
        if not value and self.products:
            raise ValueError(
                "user can't 'retire' if is responsible for products")
        if not value:
            self.done_inv = True
            self.reg_req = False
            self.req_inv = False
        return value
    
    @validates("done_inv")
    def validate_done_inv(self, key: bool, value: bool
                          ) -> Optional[bool]:
        """Rules for inventory check release.
        Cancel the request for inventorying.
        """
        if not value and not self.in_use:
            raise ValueError("'retired' user can't check inventory")
        if not value and self.reg_req:
            raise ValueError(
                "user with pending registration can't check inventory")
        if not value and not self.products:
            raise ValueError(
                "user without products attached can't check inventory")
        if not value:
            self.req_inv = False
        return value
    
    @validates("reg_req")
    def validate_reg_req(self, key: bool, value: bool
                         ) -> Optional[bool]:
        """Rules for registration request."""
        if value and self.admin:
            raise ValueError(
                "admin users can't request registration")
        if value and self.products:
            raise ValueError(
                "users with products attached can't request registration")
        if value and not self.in_use:
            raise ValueError(
                "'retired' users can't request registration")
        return value
    
    @validates("req_inv")
    def validate_req_inv(self, key: bool, value: bool
                         ) -> Optional[bool]:
        """Rules for check inventory request."""
        if value and self.admin:
            raise ValueError("admins don't need to request inventorying")
        if value and not self.in_use:
            raise ValueError("'retired' users can't request inventorying")
        if value and not self.done_inv:
            raise ValueError("user can allready check inventory")
        if value and self.reg_req:
            raise ValueError(
                "user with pending registration can't request inventorying")
        if value and not self.products:
            raise ValueError(
                "users without products can't request inventorying")
        return value



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
    
    @validates("products")
    def validate_products(self,
                          key: Optional[list[Product]],
                          value: Product
                          ) -> Optional[Product]:
        """A category that's not in use can't have products assigned."""
        if value and not self.in_use:
            raise ValueError(
                "not in use categories can't have products attached")
        return value
    
    @validates("in_use")
    def validate_in_use(self, key: bool, value: bool
                        ) -> Optional[bool]:
        """A category that has products can't 'retire'."""
        if not value and self.products:
            raise ValueError(
                "not in use categories can't have products attached")
        return value



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
    
    @validates("products")
    def validate_products(self,
                          key: Optional[list[Product]],
                          value: Product
                          ) -> Optional[Product]:
        """A supplier that's not in use can't have products assigned."""
        if value and not self.in_use:
            raise ValueError(
                "not in use supplier can't have products attached")
        return value
    
    @validates("in_use")
    def validate_in_use(self, key: bool, value: bool
                        ) -> Optional[bool]:
        """A supplier that has products can't 'retire'."""
        if not value and self.products:
            raise ValueError(
                "not in use supplier can't have products attached")
        return value



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

    
    @validates("responsable_id")
    def validate_responsable_id(self, key: int, user_id: int) -> Optional[int]:
        if not user_id:
            raise ValueError(
                "user can't be deleted or does not exist")
        with dbSession() as db_session:
            user = db_session.get(User, user_id)
            if not user:
                raise ValueError("user does not exist")
            if not user.in_use:
                raise ValueError(
                    "'retired' users can't have products attached")
            if user.reg_req:
                raise ValueError(
                    "user with pending registration " +
                    "can't have products attached")
        return user_id

    @validates("responsable")
    def validate_responsable(self,
                             key: User,
                             user: Optional[User]
                             ) -> Optional[User]:
        if not user:
            raise ValueError(
                "user does not exist")
        if not user.in_use:
            raise ValueError(
                "'retired' users can't have products attached")
        if user.reg_req:
            raise ValueError(
                "user with pending registration can't have products attached")
        return user
    
    @validates("category_id")
    def validate_category_id(self,
                             key: int,
                             category_id: int
                             ) -> Optional[int]:
        if not category_id:
            raise ValueError(
                "category can't be deleted or does not exist")
        with dbSession() as db_session:
            category = db_session.get(Category, category_id)
            if not category:
                raise ValueError("category does not exist")
            if not category.in_use:
                raise ValueError(
                    "not in use category can't have products attached")
        return category_id

    @validates("category")
    def validate_category(self,
                            key: Category,
                            category: Optional[Category]
                            ) -> Optional[Category]:
        if not category:
            raise ValueError(
                "category does not exist")
        if not category.in_use:
            raise ValueError(
                "not in use category can't have products attached")
        return category
    
    @validates("supplier_id")
    def validate_supplier_id(self,
                             key: int,
                             supplier_id: int
                             ) -> Optional[int]:
        if not supplier_id:
            raise ValueError(
                "supplier can't be deleted or does not exist")
        with dbSession() as db_session:
            supplier = db_session.get(Supplier, supplier_id)
            if not supplier:
                raise ValueError("supplier does not exist")
            if not supplier.in_use:
                raise ValueError(
                    "not in use supplier can't have products attached")
        return supplier_id

    @validates("supplier")
    def validate_supplier(self,
                            key: Supplier,
                            supplier: Optional[Supplier]
                            ) -> Optional[Supplier]:
        if not supplier:
            raise ValueError(
                "supplier does not exist")
        if not supplier.in_use:
            raise ValueError(
                "not in use supplier can't have products attached")
        return supplier
    
    @validates("min_stock")
    def validate_min_stock(self, key: int, value: int) -> Optional[int]:
        try:
            if not (value >= 0):
                raise ValueError("minimum stock must be ≥ 0")
        except TypeError:
            raise ValueError("minimum stock must be ≥ 0")
        return value
    
    @validates("ord_qty")
    def validate_ord_qty(self, key: int, value: int) -> Optional[int]:
        try:
            if not (value >= 1):
                raise ValueError("order quantity must be ≥ 1")
        except TypeError:
            raise ValueError("order quantity must be ≥ 1")
        return value
    
    @validates("to_order")
    def validate_to_order(self, key: bool, value: bool) -> Optional[bool]:
        if value and not self.in_use:
            raise ValueError("can't order not in use products")
        return value
    
    @validates("in_use")
    def validate_in_use(self, key: bool, value: bool) -> Optional[bool]:
        if not value and self.to_order:
            raise ValueError(
                "can't 'retire' a product that needs to be ordered")
        return value
