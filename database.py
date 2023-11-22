"""Database SQLAlchemy class models"""

from __future__ import annotations

from datetime import date
from os import path
from typing import Callable, List, Optional

from dotenv import load_dotenv
from sqlalchemy import (URL, ForeignKey, Index, UniqueConstraint,
                        create_engine, func, select)
from sqlalchemy.orm import (DeclarativeBase, Mapped, MappedAsDataclass,
                            declared_attr, mapped_column, relationship,
                            sessionmaker, synonym, validates)
from werkzeug.security import generate_password_hash

from blueprints.sch import clean_sch_info, sat_sch_info
from constants import Constant
from messages import Message

func: Callable

load_dotenv()

DB_URL = URL.create(
    drivername="sqlite",
    database=path.join(Constant.Basic.current_dir, Constant.Basic.db_name))
# factory for creating new database connections objects
engine = create_engine(url=DB_URL, echo=False)

# factory for Session objects
dbSession = sessionmaker(bind=engine)


class Base(MappedAsDataclass, DeclarativeBase):
    """Base class for SQLAlchemy Declarative Mapping"""

    # set table name
    @declared_attr.directive
    def __tablename__(cls):
        # pylint: disable=no-self-argument
        if cls.__name__ == "Category":
            return "categories"
        return cls.__name__.lower() + "s"

    # id for all tables
    id: Mapped[int] = mapped_column(init=False, primary_key=True)


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
    :param email: user email adress
    :param sat_group: saturday group
    :param sat_group_this_week: check if saturday group is this week
    :param clean_this_week: check if user is scheduled for cleaning

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
    - A user cannot be retired if still has products assigned
    - A product cannot be assigned to a retired user
    | products | in_use |     |
    |:--------:|:------:|:---:|
    |     0    |  False |     |
    |     0    |  True  |     |
    |    > 0   |  False | NOK |
    |    > 0   |  True  |     |

    2. products || done_inv
    - A user without products cannot check inventory;
        if a user doesn't have anymore products assigned set done_inv to True
    - Check inventory cannot be triggered for a user without products
    | products | done_inv |     |
    |:--------:|:--------:|:---:|
    |     0    |   False  | NOK |
    |     0    |   True   |     |
    |    > 0   |   False  |     |
    |    > 0   |   True   |     |

    3. !reg_req || !products
    - A product cannot be assigned to a user that requested registration
    - Request registration cannot be triggered for a user with products
    | products | reg_req |     |
    |:--------:|:-------:|:---:|
    |     0    |  False  |     |
    |     0    |   True  |     |
    |    > 0   |  False  |     |
    |    > 0   |   True  | NOK |

    4. products || !req_inv
    - A user without products cannot request inventorying;
        if a user doesn't have anymore products assigned set req_inv to False
    - Request inventorying cannot be triggered for a user without products
    | products | req_inv |     |
    |:--------:|:-------:|:---:|
    |     0    |  False  |     |
    |     0    |   True  | NOK |
    |    > 0   |  False  |     |
    |    > 0   |   True  |     |

    5. !reg_req || !admin
    - An admin cannot request registration
    - A user who requested registration cannot be admin
    | admin | reg_req |     |
    |:-----:|:-------:|:---:|
    | False |  False  |     |
    | False |   True  |     |
    |  True |  False  |     |
    |  True |   True  | NOK |

    6. !req_inv || !admin
    - An admin cannot request inventory check
    - Check inventory cannot be triggered for an admin
    | admin | req_inv |     |
    |:-----:|:-------:|:---:|
    | False |  False  |     |
    | False |   True  |     |
    |  True |  False  |     |
    |  True |   True  | NOK |

    7. in_use || done_inv
    - A retired user cannot check inventory
    - Check inventory cannot be triggered for a retired user
    | in_use | done_inv |     |
    |:------:|:--------:|:---:|
    |  False |   False  | NOK |
    |  False |   True   |     |
    |  True  |   False  |     |
    |  True  |   True   |     |

    8. in_use || !reg_req
    - A retired user cannot request registration
    - Request registration cannot be triggered for a retired user
    | in_use | reg_req |     |
    |:------:|:-------:|:---:|
    |  False |  False  |     |
    |  False |   True  | NOK |
    |  True  |  False  |     |
    |  True  |   True  |     |

    9. in_use || !req_inv
    - A retired user cannot request inventory check
    - Check inventory cannot be triggered for a retired user
    | in_use | req_inv |     |
    |:------:|:-------:|:---:|
    |  False |  False  |     |
    |  False |   True  | NOK |
    |  True  |  False  |     |
    |  True  |   True  |     |

    10. done_inv || !reg_req
    - A user that requested registration cannot check inventory
    - A user that checks inventory cannot request registration
    | done_inv | reg_req |     |
    |:--------:|:-------:|:---:|
    |   False  |  False  |     |
    |   False  |   True  | NOK |
    |   True   |  False  |     |
    |   True   |   True  |     |

    11. done_inv || !req_inv
    - A user that checks inventory cannot request check inventory
    - If check inventory triggered cancel request check
    | done_inv | req_inv |     |
    |:--------:|:-------:|:---:|
    |   False  |  False  |     |
    |   False  |   True  | NOK |
    |   True   |  False  |     |
    |   True   |   True  |     |

    12. !req_inv || !reg_req
    - A user that requested registration cannot request inventory check
    - A user that requested inventory cannot request registration
    | reg_req | req_inv |     |
    |:-------:|:-------:|:---:|
    |  False  |  False  |     |
    |  False  |   True  |     |
    |   True  |  False  |     |
    |   True  |   True  | NOK |
    """
    name: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column(repr=False)
    products: Mapped[List["Product"]] = relationship(
        default_factory=list, back_populates="responsible", repr=False)
    admin: Mapped[bool] = mapped_column(default=False)
    in_use: Mapped[bool] = mapped_column(default=True)
    done_inv: Mapped[bool] = mapped_column(default=True)
    reg_req: Mapped[bool] = mapped_column(default=True)
    req_inv: Mapped[bool] = mapped_column(default=False)
    details: Mapped[Optional[str]] = mapped_column(default="", repr=False)
    email: Mapped[Optional[str]] = mapped_column(default="", repr=False)
    sat_group: Mapped[int] = mapped_column(default=1)

    __table_args__ = (
        Index('idx_user_name', 'name'),
        Index('idx_user_in_use', 'in_use'),
    )

    username = synonym("name")

    @property
    def in_use_products(self) -> int:
        """Number of `in_use` products for user."""
        with dbSession() as db_session:
            return db_session.scalar(
                select(func.count(Product.id))
                .filter_by(responsible_id=self.id, in_use=True))

    @property
    def all_products(self) -> int:
        """Number of total products for user, including not `in_use`."""
        with dbSession() as db_session:
            return db_session.scalar(
                select(func.count(Product.id))
                .filter_by(responsible_id=self.id))

    @property
    def check_inv(self) -> bool:
        """Check inventory flag. Reverese of `done_inv`"""
        return not self.done_inv

    @property
    def sat_group_this_week(self) -> bool:
        """Check if sat_group this week."""
        with dbSession() as db_session:
            if (user_sat_group_date := db_session.scalar(
                    select(Schedule.next_date)
                    .filter_by(
                        name=sat_sch_info.name_en,
                        elem_id=self.sat_group))):
                return (user_sat_group_date.isocalendar().week ==
                        date.today().isocalendar().week)
        return False

    @property
    def clean_this_week(self) -> bool:
        """Check if user is scheduled for cleaning."""
        with dbSession() as db_session:
            if (user_cleaning_date := db_session.scalar(
                    select(Schedule.next_date)
                    .filter_by(
                        name=clean_sch_info.name_en,
                        elem_id=self.id))):
                return (user_cleaning_date.isocalendar().week ==
                        date.today().isocalendar().week)
        return False

    @validates("name")
    def validate_name(self, key: str, value: str) -> Optional[str]:
        """Check for duplicate or empty name."""
        # pylint: disable=unused-argument
        if not value or not value.strip():
            raise ValueError(Message.User.Name.Req())
        value = value.strip()
        if value != self.name:
            with dbSession() as db_session:
                if db_session.scalar(select(User).filter_by(name=value)):
                    raise ValueError(Message.User.Name.Exists(value))
        return value

    @validates("password")
    def validate_password(self, key: str, value: str) -> Optional[str]:
        """Check for missing value.
        Returns hashed `value`"""
        # pylint: disable=unused-argument
        if not value:
            raise ValueError(Message.User.Password.Req())
        return generate_password_hash(value)

    @validates("products")
    def validate_products(self,
                          key: str,
                          value: Product
                          ) -> Optional[Product]:
        """
        - A product cannot be assigned to a retired user
        - A product cannot be assigned to a user that requested registration
        """
        # pylint: disable=unused-argument
        if value:
            if not self.in_use:
                raise ValueError(Message.User.Products.Retired())
            if self.reg_req:
                raise ValueError(Message.User.Products.PendReg())
        return value

    @validates("admin")
    def validate_admin(self, key: str, value: bool
                       ) -> Optional[bool]:
        """
        - A user who requested registration cannot be admin
        - Check inventory cannot be triggered for an admin
        """
        # pylint: disable=unused-argument
        if value:
            if self.reg_req:
                raise ValueError(Message.User.Admin.PendReg())
            self.req_inv = False
        if not value:
            with dbSession() as db_session:
                admins = db_session.scalars(
                    select(User)
                    .filter_by(admin=True, in_use=True)).all()
                if len(admins) == 1 and admins[0].id == self.id:
                    raise ValueError(Message.User.Admin.LastAdmin())
        return value

    @validates("in_use")
    def validate_in_use(self, key: str, value: bool
                        ) -> Optional[bool]:
        """
        - A user cannot be retired if still has products assigned
        - Check inventory cannot be triggered for a retired user
        - Request registration cannot be triggered for a retired user
        - Check inventory cannot be triggered for a retired user
        """
        # pylint: disable=unused-argument
        if not value:
            if self.products:
                raise ValueError(Message.User.InUse.StillProd())
            self.done_inv = True
            self.reg_req = False
            self.req_inv = False
        return value

    @validates("done_inv")
    def validate_done_inv(self, key: str, value: bool) -> Optional[bool]:
        """
        - A user without products cannot check inventory
        - A retired user cannot check inventory
        - A user that requested registration cannot check inventory
        - If check inventory triggered cancel request check
        """
        # pylint: disable=unused-argument
        if not value:
            if not self.in_use:
                raise ValueError(Message.User.DoneInv.Retired())
            if self.reg_req:
                raise ValueError(Message.User.DoneInv.PendReg())
            if not self.in_use_products:
                raise ValueError(Message.User.DoneInv.NoProd())
            self.req_inv = False
        return value

    @validates("reg_req")
    def validate_reg_req(self, key: str, value: bool
                         ) -> Optional[bool]:
        """
        - Request registration cannot be triggered for a user with products
        - An admin cannot request registration
        - A retired user cannot request registration
        - A user that checks inventory cannot request registration
        - A user that requested inventory cannot request registration
        """
        # pylint: disable=unused-argument
        if value:
            if self.admin:
                raise ValueError(Message.User.RegReq.Admin())
            if not self.in_use:
                raise ValueError(Message.User.RegReq.Retired())
            if not self.done_inv:
                raise ValueError(Message.User.RegReq.CheckInv())
            if self.req_inv:
                raise ValueError(Message.User.RegReq.ReqInv())
            if self.products:
                raise ValueError(Message.User.RegReq.NoProd())
        return value

    @validates("req_inv")
    def validate_req_inv(self, key: str, value: bool
                         ) -> Optional[bool]:
        """
        - Request inventorying cannot be triggered for a user without products
        - An admin cannot request inventory check
        - A retired user cannot request inventory check
        - A user that checks inventory cannot request check inventory
        - A user that requested registration cannot request inventory check
        """
        # pylint: disable=unused-argument
        if value:
            if self.admin:
                raise ValueError(Message.User.ReqInv.Admin())
            if not self.in_use:
                raise ValueError(Message.User.ReqInv.Retired())
            if self.reg_req:
                raise ValueError(Message.User.ReqInv.PendReg())
            if not self.done_inv:
                raise ValueError(Message.User.ReqInv.CheckInv())
            if not self.in_use_products:
                raise ValueError(Message.User.ReqInv.NoProd())
        return value

    @validates("sat_group")
    def validate_sat_group(self, key: str, value: int) -> Optional[int]:
        """Validate saturday group"""
        # pylint: disable=unused-argument
        if value not in {1, 2}:
            raise ValueError("Invalid sat_group")
        return value


class Category(Base):
    """Categories database table mapping.

    :param id: category id
    :param name: category name
    :param products: list of products belonging to this category
    :param in_use: category can still be used; not obsolete
    :param description: category description, extra info
    """
    name: Mapped[str] = mapped_column(unique=True)
    products: Mapped[List["Product"]] = relationship(
        default_factory=list, back_populates="category", repr=False)
    in_use: Mapped[bool] = mapped_column(default=True)
    description: Mapped[Optional[str]] = mapped_column(
        default="", repr=False)

    __table_args__ = (
        Index('idx_category_name', 'name'),
        Index('idx_category_in_use', 'in_use'),
    )

    @property
    def in_use_products(self) -> int:
        """Number of `in_use` products for category."""
        with dbSession() as db_session:
            return db_session.scalar(
                select(func.count(Product.id))
                .filter_by(category_id=self.id, in_use=True))

    @property
    def all_products(self) -> int:
        """Number of total products for category, including not `in_use`."""
        with dbSession() as db_session:
            return db_session.scalar(
                select(func.count(Product.id))
                .filter_by(category_id=self.id))

    @validates("name")
    def validate_name(self, key: str, value: str) -> Optional[str]:
        """Check for duplicate or empty name."""
        # pylint: disable=unused-argument
        if not value or not value.strip():
            raise ValueError(Message.Category.Name.Req())
        value = value.strip()
        if value != self.name:
            with dbSession() as db_session:
                if db_session.scalar(select(Category).filter_by(name=value)):
                    raise ValueError(
                        Message.Category.Name.Exists(value))
        return value

    @validates("products")
    def validate_products(self,
                          key: str,
                          value: Product
                          ) -> Optional[Product]:
        """A category that's not in use can't have products assigned."""
        # pylint: disable=unused-argument
        if value and not self.in_use:
            raise ValueError(Message.Category.Products.Retired())
        return value

    @validates("in_use")
    def validate_in_use(self, key: str, value: bool
                        ) -> Optional[bool]:
        """A category that has products can't 'retire'."""
        # pylint: disable=unused-argument
        if not value and self.products:
            raise ValueError(Message.Category.Products.Retired())
        return value


class Supplier(Base):
    """Suppliers database table mapping.

    :param id: supplier id
    :param name: supplier name
    :param products: list of products belonging to this supplier
    :param in_use: supplier can still be used; not obsolete
    :param details: supplier details, extra info
    """
    name: Mapped[str] = mapped_column(unique=True)
    products: Mapped[List["Product"]] = relationship(
        default_factory=list, back_populates="supplier", repr=False)
    in_use: Mapped[bool] = mapped_column(default=True)
    details: Mapped[Optional[str]] = mapped_column(
        default="", repr=False)

    __table_args__ = (
        Index('idx_supplier_name', 'name'),
        Index('idx_supplier_in_use', 'in_use'),
    )

    @property
    def in_use_products(self) -> int:
        """Number of `in_use` products for supplier."""
        with dbSession() as db_session:
            return db_session.scalar(
                select(func.count(Product.id))
                .filter_by(supplier_id=self.id, in_use=True))

    @property
    def all_products(self) -> int:
        """Number of total products for supplier, including not `in_use`."""
        with dbSession() as db_session:
            return db_session.scalar(
                select(func.count(Product.id))
                .filter_by(supplier_id=self.id))

    @validates("name")
    def validate_name(self, key: str, value: str) -> Optional[str]:
        """Check for duplicate or empty name."""
        # pylint: disable=unused-argument
        if not value or not value.strip():
            raise ValueError(Message.Supplier.Name.Req())
        value = value.strip()
        if value != self.name:
            with dbSession() as db_session:
                if db_session.scalar(select(Supplier).filter_by(name=value)):
                    raise ValueError(
                        Message.Supplier.Name.Exists(value))
        return value

    @validates("products")
    def validate_products(self,
                          key: str,
                          value: Product
                          ) -> Optional[Product]:
        """A supplier that's not in use can't have products assigned."""
        # pylint: disable=unused-argument
        if value and not self.in_use:
            raise ValueError(Message.Supplier.Products.Retired())
        return value

    @validates("in_use")
    def validate_in_use(self, key: str, value: bool
                        ) -> Optional[bool]:
        """A supplier that has products can't 'retire'."""
        # pylint: disable=unused-argument
        if not value and self.products:
            raise ValueError(Message.Supplier.Products.Retired())
        return value


class Product(Base):
    """Products database table mapping.

    :param id: product id
    :param name: product short name / number / code
    :param description: produc description, extra info
    :param responsible_id: user id responsible for inventorying the product
    :param responsible: `User` class object for responsible
    :param category_id: category id of this product
    :param category: `Category` class object of this product
    :param supplier_id: supplier id of this product
    :param supplier: `Supplier` class object of this product
    :param meas_unit: measuring unit
    :param min_stock: minimum stock
    :param ord_qty: order quantity
    :param to_order: product needs to be ordered
    If `responsible` sees that shelf quantity is less than `min_stock` checks
    in the app triggering `to_order = True`. The admin will see that
    he needs to order `ord_qty` of this product.
    :param critical: product is a critical product
    :param in_use: product is not obsolete
    """
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    responsible_id = mapped_column(ForeignKey("users.id"), nullable=False)
    responsible: Mapped[User] = relationship(back_populates="products",
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

    __table_args__ = (
        Index('idx_product_name', 'name'),
        Index('idx_product_to_order', 'to_order'),
        Index('idx_product_in_use', 'in_use'),
    )

    code = synonym("name")

    @validates("name")
    def validate_name(self, key: str, value: str) -> Optional[str]:
        """Check for duplicate or empty name."""
        # pylint: disable=unused-argument
        if not value or not value.strip():
            raise ValueError(Message.Product.Name.Req())
        value = value.strip()
        if value != self.name:
            with dbSession() as db_session:
                if db_session.scalar(select(Product).filter_by(name=value)):
                    raise ValueError(
                        Message.Product.Name.Exists(value))
        return value

    @validates("description")
    def validate_description(self, key: str, value: str) -> Optional[str]:
        """Check for empty description."""
        # pylint: disable=unused-argument
        if not value or not value.strip():
            raise ValueError(Message.Product.Description.Req())
        return value.strip()

    @validates("responsible_id")
    def validate_responsible_id(self, key: str, user_id: int) -> Optional[int]:
        """Check for empty, not existing, not in use and last product."""
        # pylint: disable=unused-argument
        if not user_id:
            raise ValueError(Message.Product.Responsible.Delete())
        with dbSession() as db_session:
            user = db_session.get(User, user_id)
            if not user:
                raise ValueError(Message.User.NotExists(""))
            if not user.in_use:
                raise ValueError(Message.User.Products.Retired())
            if user.reg_req:
                raise ValueError(Message.User.Products.PendReg())
            if self.responsible_id:
                prev_user = db_session.get(User, self.responsible_id)
                # if it's the last product of previous responsible
                if prev_user.in_use_products == 1:
                    prev_user.done_inv = True
                    prev_user.req_inv = False
                    db_session.commit()
        return user_id

    @validates("responsible")
    def validate_responsible(self,
                             key: User,
                             user: Optional[User]
                             ) -> Optional[User]:
        """Check for empty, not existing, not in use and last product."""
        # pylint: disable=unused-argument
        if not user:
            raise ValueError(Message.User.NotExists(""))
        if not user.in_use:
            raise ValueError(Message.User.Products.Retired())
        if user.reg_req:
            raise ValueError(Message.User.Products.PendReg())
        with dbSession() as db_session:
            if self.responsible:
                prev_user = self.responsible
                # if it's the last product of previous responsible
                if prev_user.in_use_products == 1:
                    prev_user.done_inv = True
                    prev_user.req_inv = False
                    db_session.commit()
        return user

    @validates("category_id")
    def validate_category_id(self,
                             key: str,
                             category_id: int
                             ) -> Optional[int]:
        """Check for empty, not existing or not in use."""
        # pylint: disable=unused-argument
        if not category_id:
            raise ValueError(Message.Product.Category.Delete())
        with dbSession() as db_session:
            category = db_session.get(Category, category_id)
            if not category:
                raise ValueError(Message.Category.NotExists(""))
            if not category.in_use:
                raise ValueError(Message.Category.Products.Retired())
        return category_id

    @validates("category")
    def validate_category(self,
                          key: Category,
                          category: Optional[Category]
                          ) -> Optional[Category]:
        """Check for empty or not in use."""
        # pylint: disable=unused-argument
        if not category:
            raise ValueError(Message.Category.NotExists(""))
        if not category.in_use:
            raise ValueError(Message.Category.Products.Retired())
        return category

    @validates("supplier_id")
    def validate_supplier_id(self,
                             key: str,
                             supplier_id: int
                             ) -> Optional[int]:
        """Check for empty, not existing or not in use."""
        # pylint: disable=unused-argument
        if not supplier_id:
            raise ValueError(Message.Product.Supplier.Delete())
        with dbSession() as db_session:
            supplier = db_session.get(Supplier, supplier_id)
            if not supplier:
                raise ValueError(Message.Supplier.NotExists(""))
            if not supplier.in_use:
                raise ValueError(Message.Supplier.Products.Retired())
        return supplier_id

    @validates("supplier")
    def validate_supplier(self,
                          key: Supplier,
                          supplier: Optional[Supplier]
                          ) -> Optional[Supplier]:
        """Check for empty or not in use."""
        # pylint: disable=unused-argument
        if not supplier:
            raise ValueError(Message.Supplier.NotExists(""))
        if not supplier.in_use:
            raise ValueError(Message.Supplier.Products.Retired())
        return supplier

    @validates("meas_unit")
    def validate_meas_unit(self, key: str, value: str) -> Optional[str]:
        """Check for empty measuring unit."""
        # pylint: disable=unused-argument
        if not value or not value.strip():
            raise ValueError(Message.Product.MeasUnit.Req())
        return value.strip()

    @validates("min_stock")
    def validate_min_stock(self, key: str, value: int) -> Optional[int]:
        """Validate int value and >= 0."""
        # pylint: disable=unused-argument
        try:
            if not value >= 0:
                raise ValueError(Message.Product.MinStock.Invalid())
        except TypeError as err:
            raise ValueError(
                Message.Product.MinStock.Invalid()) from err
        return value

    @validates("ord_qty")
    def validate_ord_qty(self, key: str, value: int) -> Optional[int]:
        """Validate int value and >= 1."""
        # pylint: disable=unused-argument
        try:
            if not value >= 1:
                raise ValueError(Message.Product.OrdQty.Invalid())
        except TypeError as err:
            raise ValueError(
                Message.Product.OrdQty.Invalid()) from err
        return value

    @validates("to_order")
    def validate_to_order(self, key: str, value: bool) -> Optional[bool]:
        """Check if product is in use."""
        # pylint: disable=unused-argument
        if value and not self.in_use:
            raise ValueError(Message.Product.ToOrder.Retired())
        return value

    @validates("in_use")
    def validate_in_use(self, key: str, value: bool) -> Optional[bool]:
        """Check if product needs to be ordered."""
        # pylint: disable=unused-argument
        if not value and self.to_order:
            raise ValueError(Message.Product.InUse.ToOrder())
        return value


class Schedule(Base):
    """Schedules database table mappings.

    :param id: schedule row id
    :param name: name of the schedule
    :param type: type of the schedule (group | individual)
    :param elem_id: schedule element id (group number | user id)
    :param next_date: scheduled element date
    :param update_date: when to trigger schedule update
    :param update_interval: group - how many days to increment `next_date` and
        `update_date` when `update_date` is triggered
        individual - when users change
    The daily schedule task will search for all records where `update_date` is
    less or equal to current date:
    - if it is a group schedule update it will write to db
        `next_date` += `update_interval`
        `update_date` += `update_interval`
    - if it is an individual schedule update it will trigger a function
        in order to update all other elements
    """
    name: Mapped[str]
    type: Mapped[str]
    elem_id: Mapped[int]
    next_date: Mapped[date]
    update_date: Mapped[date]
    update_interval: Mapped[int]
    __table_args__ = (
        UniqueConstraint('name', 'elem_id', name='uq_schedule_name_elem_id'),
        Index('idx_schedule_name', 'name'),
        Index('idx_schedule_elem_id', 'elem_id'),
        Index('idx_schedule_update_date', 'update_date'),
    )

    @validates("name")
    def validate_name(self, key: str, value: str) -> Optional[str]:
        """Check for empty name."""
        # pylint: disable=unused-argument
        if not value or not value.strip():
            raise ValueError("The schedule must have a name")
        return value.strip()

    @validates("type")
    def validate_type(self, key: str, value: str) -> Optional[str]:
        """Check for empty type or not in list."""
        # pylint: disable=unused-argument
        if not value or not value.strip():
            raise ValueError("The schedule must have a type")
        value = value.strip()
        if value not in {"group", "individual"}:
            raise ValueError("Schedule type is invalid")
        return value

    @validates("elem_id")
    def validate_elem_id(self, key: str, value: int) -> Optional[int]:
        """Check for empty or less then 1 elem_id and
        unique name-elem_id combination."""
        # pylint: disable=unused-argument
        if not value:
            raise ValueError("The schedule must have an element id")
        if int(value) < 1:
            raise ValueError("Schedule elem_id is invalid")

        with dbSession() as db_session:
            if db_session.scalar(select(Schedule)
                                 .filter_by(name=self.name, elem_id=value)):
                raise ValueError("Name-Elem_id combination must be unique")
        return value

    @validates("next_date")
    def validate_next_date(self, key: str, value: date) -> Optional[date]:
        """Check for empty value."""
        # pylint: disable=unused-argument
        if not value:
            raise ValueError("The schedule must have a next date")
        if not isinstance(value, date):
            raise TypeError("Schedule's next date is invalid")
        if value < date.fromisocalendar(
                year=date.today().year,
                week=date.today().isocalendar()[1],
                day=1):
            raise ValueError(
                "The schedule's next date cannot be older than this week")
        return value

    @validates("update_date")
    def validate_update_date(self, key: str, value: date) -> Optional[date]:
        """Check for empty value or value older than `next_date` or today."""
        # pylint: disable=unused-argument
        if not value:
            raise ValueError("The schedule must have an update day")
        if not isinstance(value, date):
            raise TypeError("Schedule's update date is invalid")
        if value <= date.today():
            raise ValueError(
                "Schedule's 'update date' cannot be in the past")
        if value <= self.next_date:
            raise ValueError(
                "Schedule's 'update date' is older than 'next date'")
        return value

    @validates("update_interval")
    def validate_update_interval(
            self, key: str, value: int) -> Optional[int]:
        """Check for empty value."""
        # pylint: disable=unused-argument
        if not value:
            raise ValueError("The schedule must have an update interval")
        if int(value) < 1:
            raise ValueError("Schedule update interval is invalid")
        return value


# region: database init
# Optional creation of hidden admin (replace password)
# from sqlalchemy import event
# @event.listens_for(Base.metadata, "after_create")
# def create_hidden_admin(target, connection, **kw):
#     """Create a hidden admin user after db creation."""
#     # pylint: disable=unused-argument
#     with dbSession() as db_session:
#         if not db_session.get(User, 0):
#             admin = User(
#                 name="Admin",
#                 password="HIDDEN_ADMIN_PASSWORD",
#                 admin=True,
#                 in_use=False,
#                 reg_req=False,
#                 details="Hidden admin")
#             admin.id = 0
#             db_session.add(admin)
#             db_session.commit()

# Database creation (uncomment on first run)
# Base.metadata.create_all(bind=engine)
# endregion
