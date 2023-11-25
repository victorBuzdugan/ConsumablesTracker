"""UI Messages"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Optional

from flask import url_for
from flask_babel import LazyString, lazy_gettext, lazy_ngettext
from markupsafe import Markup

from constants import Constant


# region: helpers
class _Color(StrEnum):
    """Mapping message category to color"""
    GREEN  = "message"
    BLUE   = "info"
    YELLOW = "warning"
    RED    = "error"

_SPAN_GREY = '<span class="text-secondary">'
_SPAN_YELLOW = '<span class="text-warning">'
_SPAN_RED = '<span class="text-danger">'
_END_SPAN = "</span>"
_END_LINK = "</a>"

def _build_grey_link(link: str) -> str:
    """Build/decorate grey link"""
    return ('<a class="link-secondary link-offset-2 ' +
            'link-underline-opacity-25 link-underline-opacity-100-hover" ' +
            f'href="{link}">')

def _build_yellow_link(link: str) -> str:
    """Build/decorate yellow link"""
    return ('<a class="link-warning link-offset-2 ' +
            'link-underline-opacity-25 link-underline-opacity-100-hover" ' +
            f'href="{link}">')

def _build_red_link(link: str) -> str:
    """Build/decorate red link"""
    return ('<a class="link-danger link-offset-2 ' +
            'link-underline-opacity-25 link-underline-opacity-100-hover" ' +
            f'href="{link}">')


def _global_stats(element: str,
          all_elements: int=-1,
          in_use_elements: int=-1,
          with_link: bool=False) -> Markup:
    """Build the global stat message based on the arguments.
    
    :param element: users, categories, suppliers, products, critical_products
    :param all_elements: number of all elements
    :param in_use_elements: number of elements in use
    :param with_link: if true builds the message with a link
    """
    # prechecks
    if all_elements < 0 and in_use_elements < 0:
        raise ValueError("Invalid arguments")
    # first half
    counter = all_elements if all_elements >= 0 else in_use_elements
    match element:
        case "users":
            html_text = lazy_ngettext(
                "There is %(start_format)s%(number)s user",
                "There are %(start_format)s%(number)s users",
                counter,
                number=counter,
                start_format=(
                    _build_grey_link(url_for("main.index"))
                    if with_link else _SPAN_GREY)
            )
        case "categories":
            html_text = lazy_ngettext(
                "There is %(start_format)s%(number)s category",
                "There are %(start_format)s%(number)s categories",
                counter,
                number=counter,
                start_format=(
                    _build_grey_link(url_for("cat.categories"))
                    if with_link else _SPAN_GREY)
            )
        case "suppliers":
            html_text = lazy_ngettext(
                "There is %(start_format)s%(number)s supplier",
                "There are %(start_format)s%(number)s suppliers",
                counter,
                number=counter,
                start_format=(
                    _build_grey_link(url_for("sup.suppliers"))
                    if with_link else _SPAN_GREY)
            )
        case "products":
            html_text = lazy_ngettext(
                "There is %(start_format)s%(number)s product",
                "There are %(start_format)s%(number)s products",
                counter,
                number=counter,
                start_format=(
                    _build_grey_link(url_for("prod.products",
                                             ordered_by="code"))
                    if with_link else _SPAN_GREY)
            )
        case "critical_products":
            html_text = lazy_ngettext(
                "There is %(start_format)s%(number)s critical product",
                "There are %(start_format)s%(number)s critical products",
                counter,
                number=counter,
                start_format=(
                    _build_grey_link(url_for("prod.products",
                                             ordered_by="code"))
                    if with_link else _SPAN_GREY)
            )
        case _:
            raise ValueError(f"Invalid element '{element}'")
    html_text += _END_LINK if with_link else _END_SPAN
    # optional second half
    if all_elements < 0:
        html_text += " " + lazy_gettext("in use")
    elif all_elements > 0 and in_use_elements >= 0:
        html_text += ", " + lazy_ngettext(
            "and",
            "of which",
            all_elements
        )
        html_text += " " + _SPAN_GREY + lazy_ngettext(
            "%(number)s is in use",
            "%(number)s are in use",
            in_use_elements,
            number=in_use_elements
        )
        html_text += _END_SPAN
    return Markup(html_text)

def _indiv_stats(element: str,
          all_products: int,
          in_use_products: int) -> Markup:
    """Build the individual stat message based on the arguments.
    
    :param element: user, category, supplier
    :param all_products: number of all products of this element
    :param in_use_products: number of products in use of this element
    """
    # prechecks
    if all_products < 0 or in_use_products < 0:
        raise ValueError("Invalid arguments")
    # first half
    match element:
        case "user":
            html_text = lazy_ngettext(
                "User is responsible for %(start_format)s%(number)s product",
                "User is responsible for %(start_format)s%(number)s products",
                all_products,
                number=all_products,
                start_format=
                    _build_grey_link(url_for("prod.products",
                                       ordered_by="responsible"))
            )
        case "category":
            html_text = lazy_ngettext(
                "Category has %(start_format)s%(number)s product",
                "Category has %(start_format)s%(number)s products",
                all_products,
                number=all_products,
                start_format=
                    _build_grey_link(url_for("prod.products",
                                       ordered_by="category"))
            )
        case "supplier":
            html_text = lazy_ngettext(
                "Supplier has %(start_format)s%(number)s product",
                "Supplier has %(start_format)s%(number)s products",
                all_products,
                number=all_products,
                start_format=
                    _build_grey_link(url_for("prod.products",
                                       ordered_by="supplier"))
            )
        case _:
            raise ValueError(f"Invalid element '{element}'")
    html_text += _END_LINK
    # second half
    if all_products > 0:
        html_text += ", " + lazy_ngettext(
            "and",
            "of which",
            all_products
        )
        html_text += " " + _SPAN_GREY + lazy_ngettext(
            "%(number)s is in use",
            "%(number)s are in use",
            in_use_products,
            number=in_use_products
        )
        html_text += _END_SPAN
    return Markup(html_text)

def _strikethrough(element: str) -> Markup:
    """Build the strikethrough caption message based on argument.
    
    :param element: user, category, supplier, product, crit_product
    """
    html_text = "*"
    match element:
        case "users":
            html_text += lazy_gettext(
                "Strikethrough users are no longer in use.")
        case "categories":
            html_text += lazy_gettext(
                "Strikethrough categories are no longer in use.")
        case "suppliers":
            html_text += lazy_gettext(
                "Strikethrough suppliers are no longer in use.")
        case "products":
            html_text += lazy_gettext(
                "Strikethrough products are no longer in use.")
        case _:
            raise ValueError(f"Invalid element '{element}'")
    return Markup(html_text)

def _inv_message(requested_inv: bool, done_inventory: bool) -> Markup:
    """Return message if the user nedds to check inventory."""
    if requested_inv:
        html_text = _SPAN_YELLOW
        html_text += lazy_gettext("You requested inventorying")
        html_text += _END_SPAN
    elif done_inventory:
        html_text = _SPAN_GREY
        html_text += lazy_gettext("Inventory check not required")
        html_text += _END_SPAN
    else:
        html_text = _build_red_link(url_for("inv.inventory"))
        html_text += lazy_gettext("Check inventory")
        html_text += _END_LINK
    return Markup(html_text)

def _prod_order(products_to_order: Optional[int]) -> Markup:
    """Build the products to order message."""
    if products_to_order:
        html_text = _SPAN_RED
        html_text += lazy_ngettext(
            "There is %(start_format)s%(number)s product%(end_format)s " +
            "that needs to be ordered",
            "There are %(start_format)s%(number)s products%(end_format)s " +
            "that need to be ordered",
            products_to_order,
            number=products_to_order,
            start_format=_build_red_link(url_for("prod.products_to_order")),
            end_format=_END_LINK
        )
        html_text += _END_SPAN
    else:
        html_text = _SPAN_GREY
        html_text += lazy_gettext(
            "There are no products that need to be ordered"
        )
        html_text += _END_SPAN
    return Markup(html_text)


@dataclass(frozen=True)
class _Msg:
    """UI messages base class.
    
    :param message: the UI message
    :param category: `message` | `info` | `warning` | `error` | `None`
        `None` means it's not supposed to be flashed
    :param description: optional message extra information
    :param tested: message visually tested in the UI
        `None` means it's not possible to test this message in the UI
    """
    message: Callable[[str], LazyString]
    category: Optional[_Color] = _Color.GREEN.value
    description: Optional[str] = None
    tested: Optional[bool] = False

    def flash(self, *args, **kwargs) -> dict[str, str]:
        """Dictionary for Flask flashing."""
        return {"message": self.message(*args, **kwargs),
                "category": self.category}

    def __call__(self, *args, **kwargs) -> LazyString:
        return self.message(*args, **kwargs)
# endregion


class Message:
    """Unified messages"""
    class User:
        """User messages"""
        class Name:
            """User name messages"""
            class Requirements:
                """User name requirements"""
                MinLen = _Msg(
                    description="HTML name requirement",
                    tested=True,
                    category=None,
                    message=lambda : lazy_gettext(
                        "Must have at least %(min)i characters",
                        min=Constant.User.Name.min_length)
                )
            Required = _Msg(
                description="Displayed at user creation and authentification",
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The username is required")
            )
            LenLimit = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The username must be between %(min)i and %(max)i " +
                    "characters",
                    min=Constant.User.Name.min_length,
                    max=Constant.User.Name.max_length),
            )
            Exists = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda name: lazy_gettext(
                    "The user '%(name)s' already exists",
                    name=name)
            )
        class Password:
            """User password messages"""
            class Requirements:
                """User password requirements"""
                MinLen = _Msg(
                    description="HTML password requirement",
                    tested=True,
                    category=None,
                    message=lambda : lazy_gettext(
                        "Must have at least %(min)i characters",
                        min=Constant.User.Password.min_length)
                )
                BigLetter = _Msg(
                    description="HTML password requirement",
                    tested=True,
                    category=None,
                    message=lambda : lazy_gettext(
                        "Must have at least 1 big letter")
                )
                Number = _Msg(
                    description="HTML password requirement",
                    tested=True,
                    category=None,
                    message=lambda : lazy_gettext(
                        "Must have at least 1 number")
                )
                SpecChar = _Msg(
                    description="HTML password requirement",
                    tested=True,
                    category=None,
                    message=lambda : lazy_gettext(
                        "Must have at least 1 special character (%(symbols)s)",
                        symbols=Constant.User.Password.symbols)
                )
            Required = _Msg(
                description="Displayed at user creation and authentification",
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The password is required")
            )
            LenLimit = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The password should have at least %(min)i characters",
                    min=Constant.User.Password.min_length),
            )
            CheckRules = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "Check password rules")
            )
            Rules = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The password must have 1 big letter, 1 number, and " +
                    "1 special character (%(symbols)s)",
                    symbols=Constant.User.Password.symbols),
            )
            NotMatching = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The passwords don't match")
            )
            WrongOld = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "Wrong old password")
            )
            Changed = _Msg(
                tested=True,
                category=_Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "The password was changed")
            )
        class Products:
            """User products attr messages"""
            Retired = _Msg(
                tested=None,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't attach products to a retired user")
            )
            PendReg = _Msg(
                tested=None,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't attach products to a user " +
                    "with a pending registration")
            )
        class Admin:
            """User admin attr messages"""
            PendReg = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "A user with a pending registration can't be admin")
            )
            LastAdmin = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "You are the last admin")
            )
        class InUse:
            """User in_use attr messages"""
            StillProd = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't retire a user if he is responsible for products")
            )
        class DoneInv:
            """User done_inv attr messages"""
            Retired = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "A retired user can't check inventory")
            )
            PendReg = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "A user with a pending registration can't check inventory")
            )
            NoProd = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "A user without products attached can't check inventory")
            )
        class RegReq:
            """User reg_req attr messages"""
            Admin = _Msg(
                tested=None,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "Registration cannot be requested by an admin")
            )
            Retired = _Msg(
                tested=None,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "Registration cannot be requested by a retired user")
            )
            CheckInv = _Msg(
                tested=None,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "Registration cannot be requested by a user " +
                    "who checks inventory")
            )
            ReqInv = _Msg(
                tested=None,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "Registration cannot be requested by a user " +
                    "who has requested inventorying")
            )
            WithProd = _Msg(
                tested=None,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "Registration cannot be requested by a user " +
                    "who has products attached")
            )
        class ReqInv:
            """User req_inv attr messages"""
            Admin = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "Admins don't need to request inventorying")
            )
            Retired = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "Inventorying cannot be requested by a retired user")
            )
            PendReg = _Msg(
                tested=None,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "Inventorying cannot be requested by a user " +
                    "with a pending registration")
            )
            CheckInv = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The user can already check inventory")
            )
            NoProd = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "Inventorying cannot be requested by a user " +
                    "who has no products attached")
            )
            Sent = _Msg(
                tested=True,
                category=_Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "The inventory check request was submitted")
            )
        class Email:
            """User email messages"""
            Invalid = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The email address is incorrect")
            )
        class SatGroup:
            """User sat_group messages"""
            Invalid = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The group number doesn't exist")
            )
        NotExists = _Msg(
            description=":param name: could be empty - ''",
            tested=True,
            category=_Color.RED.value,
            message=lambda name: lazy_gettext(
                 "The user '%(name)s' does not exist",
                 name=name) if name else lazy_gettext(
                 "The user does not exist")
        )
        Login = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "Hello, %(name)s", name=name)
        )
        Logout = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda : lazy_gettext(
                "You have been logged out")
        )
        RegPending = _Msg(
            tested=True,
            category=_Color.YELLOW.value,
            message=lambda name: lazy_gettext(
                "The user '%(name)s' awaits registration approval",
                name=name),
        )
        Retired = _Msg(
            tested=True,
            category=_Color.YELLOW.value,
            message=lambda name: lazy_gettext(
                "The user '%(name)s' is retired",
                name=name),
        )
        Registered = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda : lazy_gettext(
                "The registration request was submitted. Contact an admin")
        )
        Approved = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The user '%(name)s' has been approved",
                name=name),
        )
        NoDelete = _Msg(
            tested=True,
            category=_Color.RED.value,
            message=lambda : lazy_gettext(
                "You can't delete a user if he is responsible for products")
        )
        Deleted = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The user '%(name)s' has been deleted",
                name=name)
        )
        Created = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The user '%(name)s' was created",
                name=name)
        )
        Updated = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                 "User '%(name)s' updated",
                 name=name)
        )
    class Category:
        """Category messages"""
        class Name:
            """Category name messages"""
            Required = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The category name is required")
            )
            LenLimit = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The category name must have at least %(min)s characters",
                    min=Constant.Category.Name.min_length),
            )
            Exists = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda name: lazy_gettext(
                    "The category '%(name)s' already exists",
                    name=name)
            )
        class Products:
            """Category products attr messages"""
            Disabled = _Msg(
                tested=None,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't attach products to a disabled category")
            )
        class InUse:
            """Category in_use attr messages"""
            StillProd = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't disable a category if it has products attached")
            )
        class Responsible:
            """Category responsible messages"""
            Default = _Msg(
                description="Default option for HTML select",
                tested=True,
                category=None,
                message=lambda : lazy_gettext(
                    "Select a new responsible")
            )
            Updated = _Msg(
                tested=True,
                category=_Color.GREEN.value,
                message=lambda name: lazy_gettext(
                    "The user responsible for '%(name)s' updated",
                    name=name)
            )
            Invalid = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "You have to select a new responsible first")
            )
        NotExists = _Msg(
            description=":param name: could be empty - ''",
            tested=True,
            category=_Color.RED.value,
            message=lambda name: lazy_gettext(
                 "The category '%(name)s' does not exist",
                 name=name) if name else lazy_gettext(
                 "The category does not exist")
        )
        NoDelete = _Msg(
            tested=True,
            category=_Color.RED.value,
            message=lambda : lazy_gettext(
                "You can't delete a category if it has products attached")
        )
        Deleted = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The category '%(name)s' has been deleted",
                name=name)
        )
        Created = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The category '%(name)s' was created",
                name=name)
        )
        Updated = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The category '%(name)s' was updated",
                name=name)
        )
    class Supplier:
        """Supplier messages"""
        class Name:
            """Supplier name messages"""
            Required = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The supplier name is required")
            )
            LenLimit = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The supplier name must have at least %(min)s characters",
                    min=Constant.Supplier.Name.min_length),
            )
            Exists = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda name: lazy_gettext(
                    "The supplier '%(name)s' already exists",
                    name=name)
            )
        class Products:
            """Supplier products attr messages"""
            Disabled = _Msg(
                tested=None,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't attach products to a disabled supplier")
            )
        class InUse:
            """Supplier in_use attr messages"""
            StillProd = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't disable a supplier if it has products attached")
            )
        class Responsible:
            """Supplier responsible messages"""
            Default = _Msg(
                description="Default option for HTML select",
                tested=True,
                category=None,
                message=lambda : lazy_gettext(
                    "Select a new responsible")
            )
            Updated = _Msg(
                tested=True,
                category=_Color.GREEN.value,
                message=lambda name: lazy_gettext(
                    "The user responsible for '%(name)s' updated",
                    name=name)
            )
            Invalid = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "You have to select a new responsible first")
            )
        NotExists = _Msg(
            description=":param name: could be empty - ''",
            tested=True,
            category=_Color.RED.value,
            message=lambda name: lazy_gettext(
                 "The supplier '%(name)s' does not exist",
                 name=name) if name else lazy_gettext(
                 "The supplier does not exist")
        )
        NoDelete = _Msg(
            tested=True,
            category=_Color.RED.value,
            message=lambda : lazy_gettext(
                "You can't delete a supplier if it has products attached")
        )
        Deleted = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The supplier '%(name)s' has been deleted",
                name=name)
        )
        Created = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The supplier '%(name)s' was created",
                name=name)
        )
        Updated = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The supplier '%(name)s' was updated",
                name=name)
        )
    class Product:
        """Product messages"""
        class Name:
            """Product name messages"""
            Required = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product name is required")
            )
            LenLimit = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product name must be between %(min)s and %(max)s " +
                    "characters",
                    min=Constant.Product.Name.min_length,
                    max=Constant.Product.Name.max_length)
            )
            Exists = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda name: lazy_gettext(
                    "The product '%(name)s' already exists", name=name)
            )
        class Description:
            """Product description messages"""
            Required = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product description is required")
            )
            LenLimit = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product description must be between " +
                    "%(min)s and %(max)s characters",
                    min=Constant.Product.Description.min_length,
                    max=Constant.Product.Description.max_length)
            )
        class Responsible:
            """Product responsible messages"""
            Delete = _Msg(
                tested=None,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The user can't be deleted or doesn't exist")
            )
        class Category:
            """Product category messages"""
            Delete = _Msg(
                tested=None,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The category can't be deleted or doesn't exist")
            )
        class Supplier:
            """Product supplier messages"""
            Delete = _Msg(
                tested=None,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The supplier can't be deleted or doesn't exist")
            )
        class MeasUnit:
            """Product meas_unit attr messages"""
            Required = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product measuring unit is required")
            )
        class MinStock:
            """Product min_stock attr messages"""
            Required = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product minimum stock is required")
            )
            Invalid = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product minimum stock must be ≥ %(value)s",
                    value=Constant.Product.MinStock.min_value)
            )
        class OrdQty:
            """Product ord_qty attr messages"""
            Required = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product order quantity is required")
            )
            Invalid = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The product order quantity must be ≥ %(value)s",
                    value=Constant.Product.OrdQty.min_value)
            )
        class ToOrder:
            """Product to_order attr messages"""
            Retired = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "Disabled products can't be ordered")
            )
        class InUse:
            """Product in_use attr messages"""
            ToOrder = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "You can't disable a product that must be ordered")
            )
        NotExists = _Msg(
            tested=True,
            category=_Color.RED.value,
            message=lambda name: lazy_gettext(
                 "The product '%(name)s' does not exist",
                 name=name)
        )
        Deleted = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The product '%(name)s' has been deleted",
                name=name)
        )
        Created = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The product '%(name)s' was created",
                name=name)
        )
        Updated = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda name: lazy_gettext(
                "The product '%(name)s' was updated",
                name=name)
        )
        NoSort = _Msg(
            tested=True,
            category=_Color.YELLOW.value,
            message=lambda attribute: lazy_gettext(
                "Cannot sort products by '%(attribute)s'",
                attribute=attribute)
        )
        NoOrder = _Msg(
            tested=True,
            category=_Color.YELLOW.value,
            message=lambda : lazy_gettext(
                "There are no products that must be ordered")
        )
        Ordered = _Msg(
            description="Could be one or more products",
            tested=True,
            category=_Color.GREEN.value,
            message=lambda number: lazy_ngettext(
                 "%(number)s product was removed from the order list",
                 "%(number)s products were removed from the order list",
                 number,
                 number=number)
        )
        AllOrdered = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda : lazy_gettext(
                 "All products were removed from the order list")
        )
    class Schedule:
        """Schedule messages"""
        InvalidChoice = _Msg(
            tested=None,
            category=_Color.RED.value,
            message=lambda : lazy_gettext(
                "Not a valid choice")
        )
        Review = _Msg(
            tested=True,
            category=_Color.YELLOW.value,
            message=lambda : lazy_gettext(
                "Review the schedules")
        )
        Updated = _Msg(
            tested=True,
            category=_Color.GREEN.value,
            message=lambda : lazy_gettext(
                "The schedule was updated")
        )
    class UI:
        """Interface messages"""
        class Basic:
            """Basic messages"""
            LangChd = _Msg(
                tested=True,
                category=_Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "The language was changed")
            )
        class Auth:
            """Authentification blueprint"""
            LoginReq = _Msg(
                tested=True,
                category=_Color.YELLOW.value,
                message=lambda : lazy_gettext(
                    "You have to be logged in to access this page")
            )
            AdminReq = _Msg(
                tested=True,
                category=_Color.YELLOW.value,
                message=lambda : lazy_gettext(
                    "You have to be an admin to access this page")
            )
            Wrong = _Msg(
                tested=True,
                category=_Color.RED.value,
                message=lambda : lazy_gettext(
                    "The username or password is incorrect")
            )
        class Inv:
            """Inventory blueprint"""
            Submitted = _Msg(
                tested=True,
                category=_Color.GREEN.value,
                message=lambda : lazy_gettext(
                    "The inventory has been submitted")
            )
            NotReq = _Msg(
                tested=True,
                category=_Color.BLUE.value,
                message=lambda : lazy_gettext(
                    "Inventorying is not necessary")
            )
        class Main:
            """Main blueprint"""
            LoggedInAs = _Msg(
                description="HTML",
                tested=True,
                category=None,
                message=lambda name: lazy_gettext(
                    "Logged in as %(start_format)s%(name)s%(end_format)s",
                    name=name,
                    start_format=_SPAN_GREY,
                    end_format=_END_SPAN)
            )
            YouHave = _Msg(
                description="HTML",
                tested=True,
                category=None,
                message=lambda number: lazy_ngettext(
                    "You have %(start_format)s%(number)s product " +
                    "%(end_format)s assigned",
                    "You have %(start_format)s%(number)s products " +
                    "%(end_format)s assigned",
                    number,
                    number=number,
                    start_format=_SPAN_GREY,
                    end_format=_END_SPAN) if number else lazy_gettext(
                    "%(start_format)sYou don't have products assigned" +
                    "%(end_format)s",
                    start_format=_SPAN_GREY,
                    end_format=_END_SPAN)
            )
            Inv = _Msg(
                description="Build inventory HTML message",
                tested=True,
                category=None,
                message=_inv_message
            )
            ProdToOrder = _Msg(
                description="Build products to order HTML message",
                tested=True,
                category=None,
                message=_prod_order
            )
        class Prod:
            """Products blueprint"""
            ConfirmAllOrd = _Msg(
                description="HTML",
                tested=True,
                category=None,
                message=lambda : lazy_gettext(
                    "Confirm that all products were ordered.")
            )
        class User:
            """Users blueprint"""
            AwaitsReg = _Msg(
                description="HTML",
                tested=True,
                category=None,
                message=lambda name: lazy_gettext(
                    "User awaits %(start_format)sregistration approval" +
                    "%(end_format)s",
                    start_format=_build_red_link(
                        url_for("users.approve_reg", username=name)),
                    end_format=_END_LINK)
            )
            ReqInv = _Msg(
                description="HTML",
                tested=True,
                category=None,
                message=lambda name: lazy_gettext(
                    "User requested %(start_format)sinventorying" +
                    "%(end_format)s",
                    start_format=_build_yellow_link(
                        url_for('users.approve_check_inv', username=name)),
                    end_format=_END_LINK)
            )
        class FieldsReq:
            """Fields requirements"""
            All = _Msg(
                description="HTML",
                tested=True,
                category=None,
                message=lambda : lazy_gettext(
                    "All fields are required")
            )
            AllExcEmail = _Msg(
                description="HTML",
                tested=True,
                category=None,
                message=lambda : lazy_gettext(
                    "All fields except email are required")
            )
            Underlined = _Msg(
                description="HTML",
                tested=True,
                category=None,
                message=lambda : lazy_gettext(
                    "Underlined fields are required")
            )
        class Captions:
            """HTML captions"""
            Strikethrough = _Msg(
                description="Build strikethrough HTML message",
                tested=True,
                category=None,
                message=_strikethrough
            )
            CriticalProducts = _Msg(
                description="Critical products HTML message",
                tested=True,
                category=None,
                message=lambda : lazy_gettext(
                    "*Critical products are highlighted in red.")
            )
            InvOrder = _Msg(
                description="Critical products HTML message",
                tested=True,
                category=None,
                message=lambda : lazy_gettext(
                    "*Select to order a product if current stock is less " +
                    "then minimum stock.")
            )
            BoldUsers = _Msg(
                description="Bolded users HTML message",
                tested=True,
                category=None,
                message=lambda : lazy_gettext(
                    "*Bolded users have administrative privileges.")
            )
        class Stats:
            """HTML captions"""
            Global = _Msg(
                description="Build global statistics message",
                tested=True,
                category=None,
                message=_global_stats
            )
            Indiv = _Msg(
                description="Build individual statistics message",
                tested=True,
                category=None,
                message=_indiv_stats
            )
        DelElement = _Msg(
            description="Build strikethrough message",
            tested=True,
            category=None,
            message=lambda name: lazy_gettext(
                "This will delete %(start_format)s%(name)s%(end_format)s. " +
                "You can't undo this action!",
                name=name,
                start_format=_SPAN_GREY,
                end_format=_END_SPAN)
        )
        Reassign = _Msg(
            description="HTML message",
            tested=True,
            category=None,
            message=lambda number: lazy_ngettext(
                "This will reassign %(start_format)s%(number)s product" +
                "%(end_format)s!",
                "This will reassign %(start_format)s%(number)s products" +
                "%(end_format)s!",
                number,
                number=number,
                start_format=_SPAN_GREY,
                end_format=_END_SPAN)
        )
