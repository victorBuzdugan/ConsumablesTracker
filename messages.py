"""UI Messages"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from flask_babel import LazyString, lazy_gettext

from constants import Constant


class Color(StrEnum):
    """Mapping message category to color"""
    GREEN  = "message"
    BLUE   = "info"
    YELLOW = "warning"
    RED    = "error"


@dataclass
class Msg:
    """UI messages base class.
    
    :param message: the UI message
    :param category: `message` | `info` | `warning` | `error`
    :param description: message description
    """
    message: Callable[[str], LazyString]
    category: str = Color.GREEN.value
    description: str = None
    tested: bool = False

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
            Req = Msg(
                description="Displayed at user creation and authentification",
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The username is required")
            )
            LenLimit = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Username must be between %(min)i and %(max)i characters!",
                    min=Constant.User.Name.min_length,
                    max=Constant.User.Name.max_length),
            )
            Exists = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda name: lazy_gettext(
                    "The user %(name)s allready exists", name=name)
            )
        class Password:
            """User password messages"""
            Req = Msg(
                description="Displayed at user creation and authentification",
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "The password is required")
            )
            LenLimit = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Password should have at least %(min)i characters!",
                    min=Constant.User.Password.min_length),
            )
            Rules = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Check password rules")
            )
            NotMatching = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Passwords don't match")
            )
            Changed = Msg(
                tested=False,
                category=Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "Password changed.")
            )
            WrongOld = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Wrong old password!")
            )
        class Products:
            """User products attr messages"""
            Retired = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "'Retired' users can't have products attached")
            )
            PendReg = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "User with pending registration can't have products " +
                    "attached")
            )
        class Admin:
            """User admin attr messages"""
            PendReg = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "User with pending registration can't be admin")
            )
            LastAdmin = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You are the last admin!")
            )
        class InUse:
            """User in_use attr messages"""
            StillProd = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Can't 'retire' a user if he is still responsible for " +
                    "products")
            )
        class DoneInv:
            """User done_inv attr messages"""
            Retired = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "'Retired' user can't check inventory")
            )
            PendReg = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "User with pending registration can't check inventory")
            )
            NoProd = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "User without products attached can't check inventory")
            )
        class RegReq:
            """User reg_req attr messages"""
            Admin = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Admin users can't request registration")
            )
            Retired = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "'Retired' users can't request registration")
            )
            CheckInv = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "User that checks inventory can't request registration")
            )
            ReqInv = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "User that requested inventory can't request registration")
            )
            NoProd = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Users with products attached can't request registration")
            )
        class ReqInv:
            """User req_inv attr messages"""
            Admin = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Admins don't need to request inventorying")
            )
            Retired = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "'Retired' users can't request inventorying")
            )
            PendReg = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "User with pending registration can't request inventorying")
            )
            CheckInv = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "User can allready check inventory")
            )
            NoProd = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Users without products can't request inventorying")
            )
            Sent = Msg(
                tested=False,
                category=Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "Inventory check request sent")
            )
        class Email:
            """User email messages"""
            Invalid = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Invalid email adress")
            )
        NotExists = Msg(
            description=":param name: could be empty - ''",
            tested=False,
            category=Color.RED.value,
            message=lambda name: lazy_gettext(
                 "User %(name)s does not exist",
                 name=name) if name else lazy_gettext(
                 "User does not exist")
        )
        Login = Msg(
            tested=False,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "Welcome %(name)s", name=name)
        )
        RegPending = Msg(
            tested=False,
            category=Color.YELLOW.value,
            message=lambda name: lazy_gettext(
                "User %(name)s awaits registration aproval",
                name=name),
        )
        Retired = Msg(
            tested=False,
            category=Color.YELLOW.value,
            message=lambda name: lazy_gettext(
                "User %(name)s is not in use anymore",
                name=name),
        )
        Logout = Msg(
            tested=False,
            category=Color.GREEN.value,
            message=lambda : lazy_gettext(
                "You have been logged out...")
        )
        Registered = Msg(
            tested=False,
            category=Color.GREEN.value,
            message=lambda : lazy_gettext(
                "Registration request sent. Please contact an admin.")
        )
    class Category:
        """Category messages"""
        class Name:
            """Category name messages"""
            Req = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Category name is required")
            )
            Exists = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda name: lazy_gettext(
                    "The category %(name)s allready exists", name=name)
            )
            LenLimit = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Category name must have at least %(min)s characters",
                    min=Constant.Category.Name.min_length),
            )
        class Products:
            """Category products attr messages"""
            Retired = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Not in use category can't have products attached")
            )
        class Responsible:
            """Category responsible messages"""
            Default = Msg(
                description="Default option for HTML select",
                tested=False,
                category=None,
                message=lambda : lazy_gettext(
                    "Select a new responsible")
            )
            Updated = Msg(
                tested=False,
                category=Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "Category responsible updated")
            )
            Invalid = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You have to select a new responsible first")
            )
        NotExists = Msg(
            description=":param name: could be empty - ''",
            tested=False,
            category=Color.RED.value,
            message=lambda name: lazy_gettext(
                 "Category %(name)s does not exist",
                 name=name) if name else lazy_gettext(
                 "Category does not exist")
        )
        Created = Msg(
            tested=False,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "Category '%(name)s' created",
                name=name)
        )
        NoDelete = Msg(
            tested=False,
            category=Color.RED.value,
            message=lambda : lazy_gettext(
                "Can't delete category! There are still products attached!")
        )
        Deleted = Msg(
            tested=False,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "Category '%(name)s' has been deleted",
                name=name)
        )
        Updated = Msg(
            tested=False,
            category=Color.GREEN.value,
            message=lambda : lazy_gettext(
                 "Category updated")
        )
    class Supplier:
        """Supplier messages"""
        class Name:
            """Supplier name messages"""
            Req = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Supplier name is required")
            )
            Exists = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda name: lazy_gettext(
                    "The supplier %(name)s allready exists", name=name)
            )
            LenLimit = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Supplier name must have at least %(min)s characters",
                    min=Constant.Supplier.Name.min_length),
            )
        class Products:
            """Supplier products attr messages"""
            Retired = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Not in use supplier can't have products attached")
            )
        class Responsible:
            """Supplier responsible messages"""
            Default = Msg(
                description="Default option for HTML select",
                tested=False,
                category=None,
                message=lambda : lazy_gettext(
                    "Select a new responsible")
            )
            Updated = Msg(
                tested=False,
                category=Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "Supplier responsible updated")
            )
            Invalid = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "You have to select a new responsible first")
            )
        NotExists = Msg(
            description=":param name: could be empty - ''",
            tested=False,
            category=Color.RED.value,
            message=lambda name: lazy_gettext(
                 "Supplier %(name)s does not exist",
                 name=name) if name else lazy_gettext(
                 "Supplier does not exist")
        )
        Created = Msg(
            tested=False,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "Supplier '%(name)s' created",
                name=name)
        )
        NoDelete = Msg(
            tested=False,
            category=Color.RED.value,
            message=lambda : lazy_gettext(
                "Can't delete supplier! There are still products attached!")
        )
        Deleted = Msg(
            tested=False,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "Supplier '%(name)s' has been deleted",
                name=name)
        )
        Updated = Msg(
            tested=False,
            category=Color.GREEN.value,
            message=lambda : lazy_gettext(
                 "Supplier updated")
        )
    class Product:
        """Product messages"""
        class Name:
            """Product name messages"""
            Req = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Product name is required")
            )
            Exists = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda name: lazy_gettext(
                    "The product %(name)s allready exists", name=name)
            )
            LenLimit = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Product name must be between %(min)s and %(max)s " +
                    "characters",
                    min=Constant.Product.Name.min_length,
                    max=Constant.Product.Name.max_length)
            )
        class Description:
            """Product description messages"""
            Req = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Product description is required")
            )
            LenLimit = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Product description must be between %(min)s and %(max)s " +
                    "characters",
                    min=Constant.Product.Description.min_length,
                    max=Constant.Product.Description.max_length)
            )
        class Responsible:
            """Product responsible messages"""
            Delete = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "User can't be deleted or does not exist")
            )
        class Category:
            """Product category messages"""
            Delete = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Category can't be deleted or does not exist")
            )
        class Supplier:
            """Product supplier messages"""
            Delete = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Supplier can't be deleted or does not exist")
            )
        class MeasUnit:
            """Product meas_unit attr messages"""
            Req = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Product measuring unit is required")
            )
        class MinStock:
            """Product min_stock attr messages"""
            Req = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Product minimum stock is required")
            )
            Invalid = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Minimum stock must be ≥ %(value)s",
                    value=Constant.Product.MinStock.min_value)
            )
        class OrdQty:
            """Product ord_qty attr messages"""
            Req = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Product order quantity is required")
            )
            Invalid = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Order quantity must be ≥ %(value)s",
                    value=Constant.Product.OrdQty.min_value)
            )
        class ToOrder:
            """Product to_order attr messages"""
            Retired = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Can't order not in use products")
            )
        class InUse:
            """Product in_use attr messages"""
            ToOrder = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Can't 'retire' a product that needs to be ordered")
            )
        NotExists = Msg(
            tested=False,
            category=Color.RED.value,
            message=lambda name: lazy_gettext(
                 "Product %(name)s does not exist",
                 name=name)
        )
        Created = Msg(
            tested=False,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "Product '%(name)s' created",
                name=name)
        )
        Deleted = Msg(
            tested=False,
            category=Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "Product '%(name)s' has been deleted",
                name=name)
        )
        Updated = Msg(
            tested=False,
            category=Color.GREEN.value,
            message=lambda : lazy_gettext(
                 "Product updated")
        )
        Ordered = Msg(
            description="Could be one or more products",
            tested=False,
            category=Color.GREEN.value,
            message=lambda : lazy_gettext(
                 "Products ordered")
        )
        AllOrdered = Msg(
            tested=False,
            category=Color.GREEN.value,
            message=lambda : lazy_gettext(
                 "All products ordered")
        )
        NoOrder = Msg(
            tested=False,
            category=Color.YELLOW.value,
            message=lambda : lazy_gettext(
                "There are no products that need to be ordered")
        )
        NoSort = Msg(
            tested=False,
            category=Color.YELLOW.value,
            message=lambda attribute: lazy_gettext(
                "Cannot sort products by %(attribute)s",
                attribute=attribute)
        )
    class UI:
        """Interface messages"""
        class Basic:
            """Basic messages"""
            LangChd = Msg(
                tested=False,
                category=Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "Language changed")
            )
        class Auth:
            """Authentification blueprint"""
            LoginReq = Msg(
                tested=False,
                category=Color.YELLOW.value,
                message=lambda : lazy_gettext(
                    "You have to be logged in...")
            )
            AdminReq = Msg(
                tested=False,
                category=Color.YELLOW.value,
                message=lambda : lazy_gettext(
                    "You have to be an admin...")
            )
            Wrong = Msg(
                tested=False,
                category=Color.RED.value,
                message=lambda : lazy_gettext(
                    "Wrong username or password!")
            )
        class Inv:
            """Inventory blueprint"""
            Submitted = Msg(
                tested=False,
                category=Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "Inventory has been submitted")
            )
            NotReq = Msg(
                tested=False,
                category=Color.BLUE.value,
                message=lambda : lazy_gettext(
                    "Inventory check not required")
            )

pass
