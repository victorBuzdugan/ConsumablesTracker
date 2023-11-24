"""UI Messages"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Optional

from flask_babel import LazyString, lazy_gettext, lazy_ngettext

from constants import Constant


class Color(StrEnum):
    """Mapping message category to color"""
    GREEN  = "message"
    BLUE   = "info"
    YELLOW = "warning"
    RED    = "error"


@dataclass(frozen=True)
class Msg:
    """UI messages base class.
    
    :param message: the UI message
    :param category: `message` | `info` | `warning` | `error`
    :param description: message extra information
    :param tested: message tested
    """
    message: Callable[[str], LazyString]
    category: Optional[str] = Color.GREEN.value
    description: Optional[str] = None
    tested: Optional[bool] = False

    def flash(self, *args, **kwargs) -> dict[str, str]:
        """Dictionary for Flask flashing."""
        return {"message": self.message(*args, **kwargs),
                "category": self.category}

    def __call__(self, *args, **kwargs) -> LazyString:
        return self.message(*args, **kwargs)


class Message:
    """Unified messages"""
    class User:
        """User messages"""
        class Name:
            """User name messages"""
            class Requirements:
                """User name requirements"""
                MinLen = Msg(
                    description="HTML name requirement",
                    tested=True,
                    category=None,
                    message=lambda : lazy_gettext(
                        "Must have at least %(min)i characters",
                        min=Constant.User.Name.min_length)
                )
            Required = Msg(
                description="Displayed at user creation and authentification",
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The username is required")
            )
            LenLimit = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The username must be between %(min)i and %(max)i " +
                    "characters",
                    min=Constant.User.Name.min_length,
                    max=Constant.User.Name.max_length),
            )
            Exists = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda name: lazy_gettext(
                    "The user '%(name)s' already exists",
                    name=name)
            )
        class Password:
            """User password messages"""
            class Requirements:
                """User password requirements"""
                MinLen = Msg(
                    description="HTML password requirement",
                    tested=True,
                    category=None,
                    message=lambda : lazy_gettext(
                        "Must have at least %(min)i characters",
                        min=Constant.User.Password.min_length)
                )
                BigLetter = Msg(
                    description="HTML password requirement",
                    tested=True,
                    category=None,
                    message=lambda : lazy_gettext(
                        "Must have at least 1 big letter")
                )
                Number = Msg(
                    description="HTML password requirement",
                    tested=True,
                    category=None,
                    message=lambda : lazy_gettext(
                        "Must have at least 1 number")
                )
                SpecChar = Msg(
                    description="HTML password requirement",
                    tested=True,
                    category=None,
                    message=lambda : lazy_gettext(
                        "Must have at least 1 special character (%(symbols)s)",
                        symbols=Constant.User.Password.symbols)
                )
            Required = Msg(
                description="Displayed at user creation and authentification",
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The password is required")
            )
            LenLimit = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The password should have at least %(min)i characters",
                    min=Constant.User.Password.min_length),
            )
            CheckRules = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Check password rules")
            )
            Rules = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The password must have 1 big letter, 1 number, and " +
                    "1 special character (%(symbols)s)",
                    symbols=Constant.User.Password.symbols),
            )
            NotMatching = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The passwords don't match")
            )
            WrongOld = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Wrong old password")
            )
            Changed = Msg(
                tested=True,
                category=Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "The password was changed")
            )
        class Products:
            """User products attr messages"""
            Retired = Msg(
                tested=None,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't attach products to a retired user")
            )
            PendReg = Msg(
                tested=None,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't attach products to a user " +
                    "with a pending registration")
            )
        class Admin:
            """User admin attr messages"""
            PendReg = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "A user with a pending registration can't be admin")
            )
            LastAdmin = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You are the last admin")
            )
        class InUse:
            """User in_use attr messages"""
            StillProd = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't retire a user if he is responsible for products")
            )
        class DoneInv:
            """User done_inv attr messages"""
            Retired = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "A retired user can't check inventory")
            )
            PendReg = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "A user with a pending registration can't check inventory")
            )
            NoProd = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "A user without products attached can't check inventory")
            )
        class RegReq:
            """User reg_req attr messages"""
            Admin = Msg(
                tested=None,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Registration cannot be requested by an admin")
            )
            Retired = Msg(
                tested=None,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Registration cannot be requested by a retired user")
            )
            CheckInv = Msg(
                tested=None,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Registration cannot be requested by a user " +
                    "who checks inventory")
            )
            ReqInv = Msg(
                tested=None,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Registration cannot be requested by a user " +
                    "who has requested inventorying")
            )
            WithProd = Msg(
                tested=None,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Registration cannot be requested by a user " +
                    "who has products attached")
            )
        class ReqInv:
            """User req_inv attr messages"""
            Admin = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Admins don't need to request inventorying")
            )
            Retired = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Inventorying cannot be requested by a retired user")
            )
            PendReg = Msg(
                tested=None,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Inventorying cannot be requested by a user " +
                    "with a pending registration")
            )
            CheckInv = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The user can already check inventory")
            )
            NoProd = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Inventorying cannot be requested by a user " +
                    "who has no products attached")
            )
            Sent = Msg(
                tested=True,
                category=Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "The inventory check request was submitted")
            )
        class Email:
            """User email messages"""
            Invalid = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The email address is incorrect")
            )
        class SatGroup:
            """User sat_group messages"""
            Invalid = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The group number doesn't exist")
            )
        NotExists = Msg(
            description=":param name: could be empty - ''",
            tested=True,
            category=Color.RED.value,
            message=lambda name: lazy_gettext(
                 "The user '%(name)s' does not exist",
                 name=name) if name else lazy_gettext(
                 "The user does not exist")
        )
        Login = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "Hello, %(name)s", name=name)
        )
        Logout = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda : lazy_gettext(
                "You have been logged out")
        )
        RegPending = Msg(
            tested=True,
            category=Color.YELLOW.value,
            message=lambda name: lazy_gettext(
                "The user '%(name)s' awaits registration approval",
                name=name),
        )
        Retired = Msg(
            tested=True,
            category=Color.YELLOW.value,
            message=lambda name: lazy_gettext(
                "The user '%(name)s' is retired",
                name=name),
        )
        Registered = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda : lazy_gettext(
                "The registration request was submitted. Contact an admin")
        )
        Approved = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The user '%(name)s' has been approved",
                name=name),
        )
        NoDelete = Msg(
            tested=True,
            category=Color.RED.value,
            message=lambda : lazy_gettext(
                "You can't delete a user if he is responsible for products")
        )
        Deleted = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The user '%(name)s' has been deleted",
                name=name)
        )
        Created = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The user '%(name)s' was created",
                name=name)
        )
        Updated = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                 "User '%(name)s' updated",
                 name=name)
        )
    class Category:
        """Category messages"""
        class Name:
            """Category name messages"""
            Required = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The category name is required")
            )
            LenLimit = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The category name must have at least %(min)s characters",
                    min=Constant.Category.Name.min_length),
            )
            Exists = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda name: lazy_gettext(
                    "The category '%(name)s' already exists",
                    name=name)
            )
        class Products:
            """Category products attr messages"""
            Disabled = Msg(
                tested=None,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't attach products to a disabled category")
            )
        class InUse:
            """Category in_use attr messages"""
            StillProd = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't disable a category if it has products attached")
            )
        class Responsible:
            """Category responsible messages"""
            Default = Msg(
                description="Default option for HTML select",
                tested=True,
                category=None,
                message=lambda : lazy_gettext(
                    "Select a new responsible")
            )
            Updated = Msg(
                tested=True,
                category=Color.GREEN.value,
                message=lambda name: lazy_gettext(
                    "The user responsible for '%(name)s' updated",
                    name=name)
            )
            Invalid = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You have to select a new responsible first")
            )
        NotExists = Msg(
            description=":param name: could be empty - ''",
            tested=True,
            category=Color.RED.value,
            message=lambda name: lazy_gettext(
                 "The category '%(name)s' does not exist",
                 name=name) if name else lazy_gettext(
                 "The category does not exist")
        )
        NoDelete = Msg(
            tested=True,
            category=Color.RED.value,
            message=lambda : lazy_gettext(
                "You can't delete a category if it has products attached")
        )
        Deleted = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The category '%(name)s' has been deleted",
                name=name)
        )
        Created = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The category '%(name)s' was created",
                name=name)
        )
        Updated = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The category '%(name)s' was updated",
                name=name)
        )
    class Supplier:
        """Supplier messages"""
        class Name:
            """Supplier name messages"""
            Required = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The supplier name is required")
            )
            LenLimit = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The supplier name must have at least %(min)s characters",
                    min=Constant.Supplier.Name.min_length),
            )
            Exists = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda name: lazy_gettext(
                    "The supplier '%(name)s' already exists",
                    name=name)
            )
        class Products:
            """Supplier products attr messages"""
            Disabled = Msg(
                tested=None,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't attach products to a disabled supplier")
            )
        class InUse:
            """Supplier in_use attr messages"""
            StillProd = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't disable a supplier if it has products attached")
            )
        class Responsible:
            """Supplier responsible messages"""
            Default = Msg(
                description="Default option for HTML select",
                tested=True,
                category=None,
                message=lambda : lazy_gettext(
                    "Select a new responsible")
            )
            Updated = Msg(
                tested=True,
                category=Color.GREEN.value,
                message=lambda name: lazy_gettext(
                    "The user responsible for '%(name)s' updated",
                    name=name)
            )
            Invalid = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You have to select a new responsible first")
            )
        NotExists = Msg(
            description=":param name: could be empty - ''",
            tested=True,
            category=Color.RED.value,
            message=lambda name: lazy_gettext(
                 "The supplier '%(name)s' does not exist",
                 name=name) if name else lazy_gettext(
                 "The supplier does not exist")
        )
        NoDelete = Msg(
            tested=True,
            category=Color.RED.value,
            message=lambda : lazy_gettext(
                "You can't delete a supplier if it has products attached")
        )
        Deleted = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The supplier '%(name)s' has been deleted",
                name=name)
        )
        Created = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The supplier '%(name)s' was created",
                name=name)
        )
        Updated = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The supplier '%(name)s' was updated",
                name=name)
        )
    class Product:
        """Product messages"""
        class Name:
            """Product name messages"""
            Required = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product name is required")
            )
            LenLimit = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product name must be between %(min)s and %(max)s " +
                    "characters",
                    min=Constant.Product.Name.min_length,
                    max=Constant.Product.Name.max_length)
            )
            Exists = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda name: lazy_gettext(
                    "The product '%(name)s' already exists", name=name)
            )
        class Description:
            """Product description messages"""
            Required = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product description is required")
            )
            LenLimit = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product description must be between " +
                    "%(min)s and %(max)s characters",
                    min=Constant.Product.Description.min_length,
                    max=Constant.Product.Description.max_length)
            )
        class Responsible:
            """Product responsible messages"""
            Delete = Msg(
                tested=None,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The user can't be deleted or doesn't exist")
            )
        class Category:
            """Product category messages"""
            Delete = Msg(
                tested=None,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The category can't be deleted or doesn't exist")
            )
        class Supplier:
            """Product supplier messages"""
            Delete = Msg(
                tested=None,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The supplier can't be deleted or doesn't exist")
            )
        class MeasUnit:
            """Product meas_unit attr messages"""
            Required = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product measuring unit is required")
            )
        class MinStock:
            """Product min_stock attr messages"""
            Required = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product minimum stock is required")
            )
            Invalid = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product minimum stock must be ≥ %(value)s",
                    value=Constant.Product.MinStock.min_value)
            )
        class OrdQty:
            """Product ord_qty attr messages"""
            Required = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product order quantity is required")
            )
            Invalid = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product order quantity must be ≥ %(value)s",
                    value=Constant.Product.OrdQty.min_value)
            )
        class ToOrder:
            """Product to_order attr messages"""
            Retired = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Disabled products can't be ordered")
            )
        class InUse:
            """Product in_use attr messages"""
            ToOrder = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't disable a product that must be ordered")
            )
        NotExists = Msg(
            tested=True,
            category=Color.RED.value,
            message=lambda name: lazy_gettext(
                 "The product '%(name)s' does not exist",
                 name=name)
        )
        Deleted = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The product '%(name)s' has been deleted",
                name=name)
        )
        Created = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The product '%(name)s' was created",
                name=name)
        )
        Updated = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The product '%(name)s' was updated",
                name=name)
        )
        NoSort = Msg(
            tested=True,
            category=Color.YELLOW.value,
            message=lambda attribute: lazy_gettext(
                "Cannot sort products by '%(attribute)s'",
                attribute=attribute)
        )
        NoOrder = Msg(
            tested=True,
            category=Color.YELLOW.value,
            message=lambda : lazy_gettext(
                "There are no products that must be ordered")
        )
        Ordered = Msg(
            description="Could be one or more products",
            tested=True,
            category=Color.GREEN.value,
            message=lambda number: lazy_ngettext(
                 "%(number)s product was removed from the order list",
                 "%(number)s products were removed from the order list",
                 number,
                 number=number)
        )
        AllOrdered = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda : lazy_gettext(
                 "All products were removed from the order list")
        )
    class Schedule:
        """Schedule messages"""
        InvalidChoice = Msg(
            tested=None,
            category=Color.RED.value,
            message=lambda : lazy_gettext(
                "Not a valid choice")
        )
        Review = Msg(
            tested=True,
            category=Color.YELLOW.value,
            message=lambda : lazy_gettext(
                "Review the schedules")
        )
        Updated = Msg(
            tested=True,
            category=Color.GREEN.value,
            message=lambda : lazy_gettext(
                "The schedule was updated")
        )
    class UI:
        """Interface messages"""
        class Basic:
            """Basic messages"""
            LangChd = Msg(
                tested=True,
                category=Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "The language was changed")
            )
        class Auth:
            """Authentification blueprint"""
            LoginReq = Msg(
                tested=True,
                category=Color.YELLOW.value,
                message=lambda : lazy_gettext(
                    "You have to be logged in to access this page")
            )
            AdminReq = Msg(
                tested=True,
                category=Color.YELLOW.value,
                message=lambda : lazy_gettext(
                    "You have to be an admin to access this page")
            )
            Wrong = Msg(
                tested=True,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The username or password is incorrect")
            )
        class Inv:
            """Inventory blueprint"""
            Submitted = Msg(
                tested=True,
                category=Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "The inventory has been submitted")
            )
            NotReq = Msg(
                tested=True,
                category=Color.BLUE.value,
                message=lambda : lazy_gettext(
                    "Inventorying is not necessary")
            )
        class FieldsReq:
            """Fields requirements"""
            All = Msg(
                description="HTML form fields requirements",
                tested=True,
                category=None,
                message=lambda : lazy_gettext(
                    "All fields are required")
            )
            AllExcEmail = Msg(
                description="HTML form fields requirements",
                tested=True,
                category=None,
                message=lambda : lazy_gettext(
                    "All fields except email are required")
            )
