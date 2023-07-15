"""Database SQLAlchemy class models"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import ForeignKey, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (DeclarativeBase, Mapped, MappedAsDataclass,
                            Session, declared_attr, mapped_column,
                            relationship, sessionmaker, validates, synonym)
from werkzeug.security import generate_password_hash


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

    Parameters
    ----------
    :param id: user id
    :param name: user name
    :param password: hashed user password
    :param products: user's assigned for inventorying list of products
    :param in_use_products: number of `in_use` products for user
    :param all_products: number of total products for user, \
        including not `in_use`
    :param admin: user has administrator rights
    :param in_use: user can still be used; not obsolete
    :param done_inv: user has sent the inventory
    :param check_inv: user has to check the inventory; reverese of `done_inv`
    :param reg_req: user has requested registration
    :param req_inv: user has requested inventorying
    :param details: user details, extra info

    Interlocks
    ----------
    |          | products | admin | in_use | done_inv | reg_req | req_inv |
    |:--------:|:--------:|:-----:|:------:|:--------:|:-------:|:-------:|
    | products |          |       |    x   |     x    |    x    |    x    |
    |   admin  |          |       |        |          |    x    |    x    |
    |  in_use  |     x    |       |        |     x    |    x    |    x    |
    | done_inv |     x    |       |    x   |          |    x    |    x    |
    |  reg_req |     x    |   x   |    x   |     x    |         |    x    |
    |  req_inv |     x    |   x   |    x   |     x    |    x    |         |
    
    Truth tables
    ------------
    
    1. in_use || !products
[x][ ]    - A user cannot be retired if still has products assigned
[x][ ]    - A product cannot be assigned to a retired user
    | products | in_use |     |
    |:--------:|:------:|:---:|
    |     0    |  False |     |
    |     0    |  True  |     |
    |    > 0   |  False | NOK |
    |    > 0   |  True  |     |
    
    2. products || done_inv
[ ][ ]    - A user without products cannot check inventory;
        if a user doesn't have anymore products assigned set done_inv to True
[x][ ]    - Check inventory cannot be triggered for a user without products 
    | products | done_inv |     |
    |:--------:|:--------:|:---:|
    |     0    |   False  | NOK |
    |     0    |   True   |     |
    |    > 0   |   False  |     |
    |    > 0   |   True   |     |
    
    3. !reg_req || !products
[x][ ]    - A product cannot be assigned to a user that requested registration
[x][ ]    - Request registration cannot be triggered for a user with products
    | products | reg_req |     |
    |:--------:|:-------:|:---:|
    |     0    |  False  |     |
    |     0    |   True  |     |
    |    > 0   |  False  |     |
    |    > 0   |   True  | NOK |

    4. products || !req_inv
[ ][ ]    - A user without products cannot request inventorying;
        if a user doesn't have anymore products assigned set req_inv to False
[x][ ]    - Request inventorying cannot be triggered for a user without products
    | products | req_inv |     |
    |:--------:|:-------:|:---:|
    |     0    |  False  |     |
    |     0    |   True  | NOK |
    |    > 0   |  False  |     |
    |    > 0   |   True  |     |

    5. !reg_req || !admin
[x][ ]    - An admin cannot request registration
[x][ ]    - A user who requested registration cannot be admin
    | admin | reg_req |     |
    |:-----:|:-------:|:---:|
    | False |  False  |     |
    | False |   True  |     |
    |  True |  False  |     |
    |  True |   True  | NOK |

    6. !req_inv || !admin
[x][ ]    - An admin cannot request inventory check
[x][ ]    - Check inventory cannot be triggered for an admin
    | admin | req_inv |     |
    |:-----:|:-------:|:---:|
    | False |  False  |     |
    | False |   True  |     |
    |  True |  False  |     |
    |  True |   True  | NOK |

    7. in_use || done_inv
[x][ ]    - A retired user cannot check inventory
[x][ ]    - Check inventory cannot be triggered for a retired user
    | in_use | done_inv |     |
    |:------:|:--------:|:---:|
    |  False |   False  | NOK |
    |  False |   True   |     |
    |  True  |   False  |     |
    |  True  |   True   |     |

    8. in_use || !reg_req
[x][ ]    - A retired user cannot request registration
[x][ ]    - Request registration cannot be triggered for a retired user
    | in_use | reg_req |     |
    |:------:|:-------:|:---:|
    |  False |  False  |     |
    |  False |   True  | NOK |
    |  True  |  False  |     |
    |  True  |   True  |     |

    9. in_use || !req_inv
[x][ ]    - A retired user cannot request inventory check
[x][ ]    - Check inventory cannot be triggered for a retired user
    | in_use | req_inv |     |
    |:------:|:-------:|:---:|
    |  False |  False  |     |
    |  False |   True  | NOK |
    |  True  |  False  |     |
    |  True  |   True  |     |

    10. done_inv || !reg_req
[x][ ]    - A user that requested registration cannot check inventory
[x][ ]    - A user that checks inventory cannot request registration
    | done_inv | reg_req |     |
    |:--------:|:-------:|:---:|
    |   False  |  False  |     |
    |   False  |   True  | NOK |
    |   True   |  False  |     |
    |   True   |   True  |     |

    11. done_inv || !req_inv
[x][ ]    - A user that checks inventory cannot request check inventory
[x][ ]    - If check inventory triggered cancel request check
    | done_inv | req_inv |     |
    |:--------:|:-------:|:---:|
    |   False  |  False  |     |
    |   False  |   True  | NOK |
    |   True   |  False  |     |
    |   True   |   True  |     |

    12. !req_inv || !reg_req
[x][ ]    - A user that requested registration cannot request inventory check
[x][ ]    - A user that requested inventory cannot request registration
    | reg_req | req_inv |     |
    |:-------:|:-------:|:---:|
    |  False  |  False  |     |
    |  False  |   True  |     |
    |   True  |  False  |     |
    |   True  |   True  | NOK |
    """
    password: Mapped[str] = mapped_column(repr=False)
    products: Mapped[List["Product"]] = relationship(
        default_factory=list, back_populates="responsable", repr=False)
    admin: Mapped[bool] = mapped_column(default=False)
    in_use: Mapped[bool] = mapped_column(default=True)
    done_inv: Mapped[bool] = mapped_column(default=True)
    reg_req: Mapped[bool] = mapped_column(default=True)
    req_inv: Mapped[bool] = mapped_column(default=False)
    details: Mapped[Optional[str]] = mapped_column(default="", repr=False)

    username = synonym("name")

    @property
    def in_use_products(self) -> int:
        """Number of `in_use` products for user."""
        with dbSession() as db_session:
            return db_session.query(Product).\
                filter_by(in_use=True, responsable_id=self.id).count()

    @property
    def all_products(self) -> int:
        """Number of total products for user, including not `in_use`."""
        with dbSession() as db_session:
            return db_session.query(Product).\
                filter_by(responsable_id=self.id).count()

    @property
    def check_inv(self) -> bool:
        """Check inventory flag. Reverese of `done_inv`"""
        return not self.done_inv
  
    @validates("name")
    def validate_name(self, key: str, value: str) -> Optional[str]:
        """Check for duplicate or empty name."""
        if not value:
            raise ValueError("User must have a name")
        if value != self.name:
            with dbSession() as db_session:
                if db_session.scalar(select(User).filter_by(name=value)):
                    raise ValueError(f"User {value} allready exists")
        return value
    
    @validates("password")
    def validate_password(self, key: str, value: str) -> Optional[str]:
        if not value:
            raise ValueError("User must have a password")
        return generate_password_hash(value)

    @validates("products")
    def validate_products(self,
                          key: Optional[list[Product]],
                          value: Product
                          ) -> Optional[Product]:
        """
        - A product cannot be assigned to a retired user
        - A product cannot be assigned to a user that requested registration
        """
        if value:
            if not self.in_use:
                raise ValueError(
                    "'Retired' users can't have products attached")
            if self.reg_req:
                raise ValueError(
                "User with pending registration can't have products attached")
        return value

    @validates("admin")
    def validate_admin(self, key: bool, value: bool
                       ) -> Optional[bool]:
        """
        - A user who requested registration cannot be admin
        - Check inventory cannot be triggered for an admin
        """
        if value and self.reg_req:
            raise ValueError("User with pending registration can't be admin")
        self.req_inv = False
        return value
    
    @validates("in_use")
    def validate_in_use(self, key: bool, value: bool
                        ) -> Optional[bool]:
        """
        - A user cannot be retired if still has products assigned
        - Check inventory cannot be triggered for a retired user
        - Request registration cannot be triggered for a retired user
        - Check inventory cannot be triggered for a retired user
        """
        if not value:
            if self.products:
                raise ValueError(
                    "Can't 'retire' a user if he is still responsible " +
                        "for products")
            self.done_inv = True
            self.reg_req = False
            self.req_inv = False
        return value

    @validates("done_inv")
    def validate_done_inv(self, key: bool, value: bool) -> Optional[bool]:
        """
        - A user without products cannot check inventory
        - A retired user cannot check inventory
        - A user that requested registration cannot check inventory
        - If check inventory triggered cancel request check
        """
        if not value:
            if not self.in_use:
                raise ValueError("'Retired' user can't check inventory")
            if self.reg_req:
                raise ValueError(
                    "User with pending registration can't check inventory")
            if not self.products:
                raise ValueError(
                    "User without products attached can't check inventory")
            self.req_inv = False
        return value
    
    @validates("reg_req")
    def validate_reg_req(self, key: bool, value: bool
                         ) -> Optional[bool]:
        """
        - Request registration cannot be triggered for a user with products
        - An admin cannot request registration
        - A retired user cannot request registration
        - A user that checks inventory cannot request registration
        - A user that requested inventory cannot request registration
        """
        if value:
            if self.admin:
                raise ValueError("Admin users can't request registration")
            if not self.in_use:
                raise ValueError("'Retired' users can't request registration")
            if not self.done_inv:
                raise ValueError(
                    "User that checks inventory can't request registration")
            if self.req_inv:
                raise ValueError(
                    "User that requested inventory can't request registration")
            if self.products:
                raise ValueError(
                    "Users with products attached can't request registration")
        return value
    
    @validates("req_inv")
    def validate_req_inv(self, key: bool, value: bool
                         ) -> Optional[bool]:
        """
        - Request inventorying cannot be triggered for a user without products
        - An admin cannot request inventory check
        - A retired user cannot request inventory check
        - A user that checks inventory cannot request check inventory
        - A user that requested registration cannot request inventory check
        """
        if value:
            if self.admin:
                raise ValueError("Admins don't need to request inventorying")
            if not self.in_use:
                raise ValueError("'Retired' users can't request inventorying")
            if self.reg_req:
                raise ValueError(
                    "User with pending registration can't request " +
                        "inventorying")
            if not self.done_inv:
                raise ValueError("User can allready check inventory")
            if not self.products:
                raise ValueError(
                    "Users without products can't request inventorying")
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
        default="", repr=False)
    

    @validates("name")
    def validate_name(self, key: str, value: str) -> Optional[str]:
        """Check for duplicate or empty name."""
        if not value:
            raise ValueError("Category must have a name")
        if value != self.name:
            with dbSession() as db_session:
                if db_session.scalar(select(Category).filter_by(name=value)):
                    raise ValueError(f"Category {value} allready exists")
        return value


    @validates("products")
    def validate_products(self,
                          key: Optional[list[Product]],
                          value: Product
                          ) -> Optional[Product]:
        """A category that's not in use can't have products assigned."""
        if value and not self.in_use:
            raise ValueError(
                "Not in use categories can't have products attached")
        return value
    
    @validates("in_use")
    def validate_in_use(self, key: bool, value: bool
                        ) -> Optional[bool]:
        """A category that has products can't 'retire'."""
        if not value and self.products:
            raise ValueError(
                "Not in use categories can't have products attached")
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
        default="", repr=False)


    @validates("name")
    def validate_name(self, key: str, value: str) -> Optional[str]:
        """Check for duplicate or empty name."""
        if not value:
            raise ValueError("Supplier must have a name")
        if value != self.name:
            with dbSession() as db_session:
                if db_session.scalar(select(Supplier).filter_by(name=value)):
                    raise ValueError(f"Supplier {value} allready exists")
        return value


    @validates("products")
    def validate_products(self,
                          key: Optional[list[Product]],
                          value: Product
                          ) -> Optional[Product]:
        """A supplier that's not in use can't have products assigned."""
        if value and not self.in_use:
            raise ValueError(
                "Not in use supplier can't have products attached")
        return value
    
    @validates("in_use")
    def validate_in_use(self, key: bool, value: bool
                        ) -> Optional[bool]:
        """A supplier that has products can't 'retire'."""
        if not value and self.products:
            raise ValueError(
                "Not in use supplier can't have products attached")
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

    
    @validates("name")
    def validate_name(self, key: str, value: str) -> Optional[str]:
        """Check for duplicate or empty name."""
        if not value:
            raise ValueError("Product must have a name")
        if value != self.name:
            with dbSession() as db_session:
                if db_session.scalar(select(Product).filter_by(name=value)):
                    raise ValueError(f"Product {value} allready exists")
        return value
    
    @validates("description")
    def validate_description(self, key: str, value: str) -> Optional[str]:
        """Check for empty description."""
        if not value:
            raise ValueError("Product must have a description")
        return value

    @validates("responsable_id")
    def validate_responsable_id(self, key: int, user_id: int) -> Optional[int]:
        if not user_id:
            raise ValueError(
                "User can't be deleted or does not exist")
        with dbSession() as db_session:
            user = db_session.get(User, user_id)
            if not user:
                raise ValueError("User does not exist")
            if not user.in_use:
                raise ValueError(
                    "'Retired' users can't have products attached")
            if user.reg_req:
                raise ValueError(
                    "User with pending registration " +
                    "can't have products attached")
        return user_id

    @validates("responsable")
    def validate_responsable(self,
                             key: User,
                             user: Optional[User]
                             ) -> Optional[User]:
        if not user:
            raise ValueError(
                "User does not exist")
        if not user.in_use:
            raise ValueError(
                "'Retired' users can't have products attached")
        if user.reg_req:
            raise ValueError(
                "User with pending registration can't have products attached")
        return user
    
    @validates("category_id")
    def validate_category_id(self,
                             key: int,
                             category_id: int
                             ) -> Optional[int]:
        if not category_id:
            raise ValueError(
                "Category can't be deleted or does not exist")
        with dbSession() as db_session:
            category = db_session.get(Category, category_id)
            if not category:
                raise ValueError("Category does not exist")
            if not category.in_use:
                raise ValueError(
                    "Not in use category can't have products attached")
        return category_id

    @validates("category")
    def validate_category(self,
                            key: Category,
                            category: Optional[Category]
                            ) -> Optional[Category]:
        if not category:
            raise ValueError(
                "Category does not exist")
        if not category.in_use:
            raise ValueError(
                "Not in use category can't have products attached")
        return category
    
    @validates("supplier_id")
    def validate_supplier_id(self,
                             key: int,
                             supplier_id: int
                             ) -> Optional[int]:
        if not supplier_id:
            raise ValueError(
                "Supplier can't be deleted or does not exist")
        with dbSession() as db_session:
            supplier = db_session.get(Supplier, supplier_id)
            if not supplier:
                raise ValueError("Supplier does not exist")
            if not supplier.in_use:
                raise ValueError(
                    "Not in use supplier can't have products attached")
        return supplier_id

    @validates("supplier")
    def validate_supplier(self,
                            key: Supplier,
                            supplier: Optional[Supplier]
                            ) -> Optional[Supplier]:
        if not supplier:
            raise ValueError(
                "Supplier does not exist")
        if not supplier.in_use:
            raise ValueError(
                "Not in use supplier can't have products attached")
        return supplier
    
    @validates("min_stock")
    def validate_min_stock(self, key: int, value: int) -> Optional[int]:
        try:
            if not (value >= 0):
                raise ValueError("Minimum stock must be ≥ 0")
        except TypeError:
            raise ValueError("Minimum stock must be ≥ 0")
        return value
    
    @validates("ord_qty")
    def validate_ord_qty(self, key: int, value: int) -> Optional[int]:
        try:
            if not (value >= 1):
                raise ValueError("Order quantity must be ≥ 1")
        except TypeError:
            raise ValueError("Order quantity must be ≥ 1")
        return value
    
    @validates("to_order")
    def validate_to_order(self, key: bool, value: bool) -> Optional[bool]:
        if value and not self.in_use:
            raise ValueError("Can't order not in use products")
        return value
    
    @validates("in_use")
    def validate_in_use(self, key: bool, value: bool) -> Optional[bool]:
        if not value and self.to_order:
            raise ValueError(
                "Can't 'retire' a product that needs to be ordered")
        return value
