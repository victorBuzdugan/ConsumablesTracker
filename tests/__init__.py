"""Tests constants and helpers."""

from dataclasses import dataclass
from datetime import date, timedelta
from os import getenv
from pathlib import Path
from urllib.parse import quote

from werkzeug.test import TestResponse

from blueprints.sch import clean_sch_info, sat_sch_info
from database import User
from constants import Constant
from daily_task import db_backup_name
from helpers import logger

TEST_DB_NAME = "." + Constant.Basic.db_name

PROD_DB = Path(Constant.Basic.current_dir, TEST_DB_NAME)
BACKUP_DB = db_backup_name(PROD_DB)
ORIG_DB = PROD_DB.with_stem(PROD_DB.stem + "_orig")
TEMP_DB = PROD_DB.with_stem(PROD_DB.stem + "_temp")
LOG_FILE = Path(logger.handlers[0].baseFilename)


# region helpers
def redirected_to(final_url: str,
                response: TestResponse,
                total_redirects: int = 1) -> bool:
    """Test if the `final_url` is the final redirect in `response`.
    
    :param final_url: the url to check
    :param response: the client response
    :param total_redirects: the history length
    """
    assert len(response.history) == total_redirects
    for num in range(total_redirects):
        assert response.history[num].status_code == 302
    assert response.status_code == 200
    assert quote(response.request.path) == final_url
    return True
# endregion


# region: users
@dataclass(frozen=True)
class ValidUser:
    """Valid user data."""
    name: str = "x" * Constant.User.Name.min_length
    password: str = "P@ssw0rd"
    email: str = "email@example.com"
    sat_group: int = 1
    details = ""
    admin = True

@dataclass(frozen=True)
class InvalidUser:
    """Invalid user data."""
    short_name: str = "x" * (Constant.User.Name.min_length - 1)
    long_name: str = "x" * (Constant.User.Name.max_length + 1)
    short_password: str = "x" * (Constant.User.Password.min_length - 1)
    only_lowercase_password: str = "x" * Constant.User.Password.min_length
    no_special_char_password: str = ("X1" +
                                     "x" * Constant.User.Password.min_length)
    no_uppercase_password: str = ("#1" +
                                  "x" * Constant.User.Password.min_length)
    no_number_password: str = ("#X" +
                               "x" * Constant.User.Password.min_length)

test_users: tuple[dict[str, str|int|bool]] = (
    {
        "details": "Hidden admin",
        "id": 0,
        "name": "Admin",
        "password": getenv("ADMIN_PASSW"),
        "admin": True,
        "in_use": False,
        "done_inv": True,
        "reg_req": False,
        "req_inv": False,
        "email": "",
        "sat_group": 1,
        "has_products": False,
        # user is in use and not requested registration
        "active": False,
    },
    {
        "details": "Admin user with products",
        "id": 1,
        "name": "user1",
        "password": "Q!111111",
        "admin": True,
        "in_use": True,
        "done_inv": True,
        "reg_req": False,
        "req_inv": False,
        "email": "consumablestracker+user1@gmail.com",
        "sat_group": 1,
        "has_products": True,
        "active": True,
    },
    {
        "details": "Admin user with products",
        "id": 2,
        "name": "user2",
        "password": "Q!222222",
        "admin": True,
        "in_use": True,
        "done_inv": True,
        "reg_req": False,
        "req_inv": False,
        "email": "consumablestracker+user2@gmail.com",
        "sat_group": 2,
        "has_products": True,
        "active": True,
    },
    {
        "details": "Normal user with products",
        "id": 3,
        "name": "user3",
        "password": "Q!333333",
        "admin": False,
        "in_use": True,
        "done_inv": True,
        "reg_req": False,
        "req_inv": False,
        "email": "consumablestracker+user3@gmail.com",
        "sat_group": 1,
        "has_products": True,
        "active": True,
    },
    {
        "details": "Normal user with products",
        "id": 4,
        "name": "user4",
        "password": "Q!444444",
        "admin": False,
        "in_use": True,
        "done_inv": True,
        "reg_req": False,
        "req_inv": False,
        "email": "consumablestracker+user4@gmail.com",
        "sat_group": 2,
        "has_products": True,
        "active": True,
    },
    {
        "details": "Normal user that requested registration",
        "id": 5,
        "name": "user5",
        "password": "Q!555555",
        "admin": False,
        "in_use": True,
        "done_inv": True,
        "reg_req": True,
        "req_inv": False,
        "email": "consumablestracker+user5@gmail.com",
        "sat_group": 1,
        "has_products": False,
        "active": False,
    },
    {
        "details": "Normal user that is retired",
        "id": 6,
        "name": "user6",
        "password": "Q!666666",
        "admin": False,
        "in_use": False,
        "done_inv": True,
        "reg_req": False,
        "req_inv": False,
        "email": "consumablestracker+user6@gmail.com",
        "sat_group": 1,
        "has_products": False,
        "active": False,
    },
    {
        "details": "Normal user without products",
        "id": 7,
        "name": "user7",
        "password": "Q!777777",
        "admin": False,
        "in_use": True,
        "done_inv": True,
        "reg_req": False,
        "req_inv": False,
        "email": "",
        "sat_group": 1,
        "has_products": False,
        "active": True,
    },
)
# endregion


# region: categories
@dataclass(frozen=True)
class ValidCategory:
    """Valid category data."""
    name: str = "x" * Constant.Category.Name.min_length
    details: str = ""
    in_use: str = "on"

@dataclass(frozen=True)
class InvalidCategory:
    """Invalid category data."""
    short_name: str = "x" * (Constant.Category.Name.min_length - 1)

test_categories: tuple[dict[str, str|int|bool]] = (
    {
        "details": "Normal in use category",
        "id": 1,
        "name": "Household",
        "in_use": True,
        "has_products": True,
    },
    {
        "details": "Normal in use category",
        "id": 2,
        "name": "Personal",
        "in_use": True,
        "has_products": True,
    },
    {
        "details": "Normal in use category",
        "id": 3,
        "name": "Electronics",
        "in_use": True,
        "has_products": True,
    },
    {
        "details": "Normal in use category",
        "id": 4,
        "name": "Kids",
        "in_use": True,
        "has_products": True,
    },
    {
        "details": "Normal in use category",
        "id": 5,
        "name": "Health",
        "in_use": True,
        "has_products": True,
    },
    {
        "details": "Normal in use category",
        "id": 6,
        "name": "Groceries",
        "in_use": True,
        "has_products": True,
    },
    {
        "details": "Normal in use category",
        "id": 7,
        "name": "Pets",
        "in_use": True,
        "has_products": True,
    },
    {
        "details": "Disabled category",
        "id": 8,
        "name": "Other category",
        "in_use": False,
        "has_products": False,
    },
)
# endregion


# region: suppliers
@dataclass(frozen=True)
class ValidSupplier:
    """Valid supplier data."""
    name: str = "x" * Constant.Supplier.Name.min_length
    details: str = ""
    in_use: str = "on"

@dataclass(frozen=True)
class InvalidSupplier:
    """Invalid supplier data."""
    short_name: str = "x" * (Constant.Supplier.Name.min_length - 1)

test_suppliers: tuple[dict[str, str|int|bool]] = (
    {
        "details": "Normal in use supplier",
        "id": 1,
        "name": "Amazon",
        "in_use": True,
        "has_products": True,
    },
    {
        "details": "Normal in use supplier",
        "id": 2,
        "name": "eBay",
        "in_use": True,
        "has_products": True,
    },
    {
        "details": "Normal in use supplier",
        "id": 3,
        "name": "Kaufland",
        "in_use": True,
        "has_products": True,
    },
    {
        "details": "Normal in use supplier",
        "id": 4,
        "name": "Carrefour",
        "in_use": True,
        "has_products": True,
    },
    {
        "details": "Disabled supplier",
        "id": 5,
        "name": "Other supplier",
        "in_use": False,
        "has_products": False,
    },
)
# endregion


# region: products
@dataclass(frozen=True)
class ValidProduct:
    """Valid product data."""
    name: str = "x" * Constant.Product.Name.min_length
    description: str = "x" * Constant.Product.Description.min_length
    responsible_id: int = 1
    category_id: int = 1
    supplier_id: int = 1
    meas_unit: str = "pc"
    min_stock: int = Constant.Product.MinStock.min_value
    ord_qty: int = Constant.Product.OrdQty.min_value
    to_order: bool = ""
    critical: bool = ""
    in_use: bool = "on"

@dataclass(frozen=True)
class InvalidProduct:
    """Invalid product data."""
    short_name: str = "x" * (Constant.Product.Name.min_length - 1)
    long_name: str = "x" * (Constant.Product.Name.max_length + 1)
    short_description: str = "x" * (Constant.Product.Description.min_length - 1)
    long_description: str = "x" * (Constant.Product.Description.max_length + 1)
    responsible_id: int = [user["id"] for user in test_users][-1] + 1
    category_id: int = [cat["id"] for cat in test_categories][-1] + 1
    supplier_id: int = [sup["id"] for sup in test_suppliers][-1] + 1
    small_min_stock: int = Constant.Product.MinStock.min_value - 1
    small_ord_qty: int = Constant.Product.OrdQty.min_value - 1

test_products: tuple[dict[str, str|int|bool]] = (
    {   "name": "Toilet paper",
        "description": "Toilet paper 3-Ply",
        "id": 1,
        "responsible_id": 2,
        "category_id": 1,
        "supplier_id": 3,
        "meas_unit": "roll",
        "min_stock": 5,
        "ord_qty": 20,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Paper towels",
        "description": "Kitchen paper towels",
        "id": 2,
        "responsible_id": 2,
        "category_id": 1,
        "supplier_id": 4,
        "meas_unit": "roll",
        "min_stock": 2,
        "ord_qty": 4,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Trash bag small",
        "description": "Trash bag 35l",
        "id": 3,
        "responsible_id": 2,
        "category_id": 1,
        "supplier_id": 4,
        "meas_unit": "bag",
        "min_stock": 3,
        "ord_qty": 10,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Trash bag large",
        "description": "Trash bag 70l",
        "id": 4,
        "responsible_id": 2,
        "category_id": 1,
        "supplier_id": 4,
        "meas_unit": "bag",
        "min_stock": 3,
        "ord_qty": 10,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Glass cleaner",
        "description": "Glass cleaner",
        "id": 5,
        "responsible_id": 2,
        "category_id": 1,
        "supplier_id": 1,
        "meas_unit": "bottle",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "BathroomCleaner",
        "description": "Bathroom cleaner",
        "id": 6,
        "responsible_id": 2,
        "category_id": 1,
        "supplier_id": 1,
        "meas_unit": "bottle",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Wood cleaner",
        "description": "Pronto wood cleaner",
        "id": 7,
        "responsible_id": 2,
        "category_id": 1,
        "supplier_id": 1,
        "meas_unit": "spray",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Kitchen cleaner",
        "description": "Kitchen cleaner",
        "id": 8,
        "responsible_id": 2,
        "category_id": 1,
        "supplier_id": 1,
        "meas_unit": "spray",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Kitchen sponge",
        "description": "Kitchen scrub sponge",
        "id": 9,
        "responsible_id": 2,
        "category_id": 1,
        "supplier_id": 4,
        "meas_unit": "pc",
        "min_stock": 2,
        "ord_qty": 8,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Cleaning Cloth",
        "description": "Microfibre Cleaning Cloth",
        "id": 10,
        "responsible_id": 2,
        "category_id": 1,
        "supplier_id": 3,
        "meas_unit": "pc",
        "min_stock": 1,
        "ord_qty": 6,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "AA Batteries",
        "description": "Ultra AA Batteries",
        "id": 11,
        "responsible_id": 1,
        "category_id": 3,
        "supplier_id": 2,
        "meas_unit": "pc",
        "min_stock": 2,
        "ord_qty": 8,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "AAA Batteries",
        "description": "Ultra AAA Batteries",
        "id": 12,
        "responsible_id": 1,
        "category_id": 3,
        "supplier_id": 2,
        "meas_unit": "pc",
        "min_stock": 2,
        "ord_qty": 6,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Laundry Deterg",
        "description": "Powder Laundry Detergent",
        "id": 13,
        "responsible_id": 2,
        "category_id": 1,
        "supplier_id": 4,
        "meas_unit": "bag",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Matches",
        "description": "Matches",
        "id": 14,
        "responsible_id": 1,
        "category_id": 1,
        "supplier_id": 4,
        "meas_unit": "box",
        "min_stock": 1,
        "ord_qty": 3,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Facial tissues",
        "description": "Facial tissues",
        "id": 15,
        "responsible_id": 3,
        "category_id": 2,
        "supplier_id": 1,
        "meas_unit": "pack",
        "min_stock": 2,
        "ord_qty": 10,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Personal wipes",
        "description": "Personal cleansing wipes",
        "id": 16,
        "responsible_id": 3,
        "category_id": 2,
        "supplier_id": 1,
        "meas_unit": "pack",
        "min_stock": 1,
        "ord_qty": 6,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Eyeglass wipes",
        "description": "Eyeglass wipes",
        "id": 17,
        "responsible_id": 1,
        "category_id": 2,
        "supplier_id": 1,
        "meas_unit": "pack",
        "min_stock": 0,
        "ord_qty": 2,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "PhPr cartridge",
        "description": "Photo printer ink cartridge",
        "id": 18,
        "responsible_id": 1,
        "category_id": 3,
        "supplier_id": 1,
        "meas_unit": "pc",
        "min_stock": 1,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "PhPr paper",
        "description": "Photo printer paper",
        "id": 19,
        "responsible_id": 1,
        "category_id": 3,
        "supplier_id": 1,
        "meas_unit": "pc",
        "min_stock": 10,
        "ord_qty": 20,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Drawing paper",
        "description": "Drawing paper",
        "id": 20,
        "responsible_id": 4,
        "category_id": 4,
        "supplier_id": 1,
        "meas_unit": "pc",
        "min_stock": 10,
        "ord_qty": 20,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Drawing crayons",
        "description": "Drawing crayons",
        "id": 21,
        "responsible_id": 4,
        "category_id": 4,
        "supplier_id": 1,
        "meas_unit": "pc",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Car cleaner",
        "description": "Car plastics cleaner",
        "id": 22,
        "responsible_id": 1,
        "category_id": 1,
        "supplier_id": 4,
        "meas_unit": "spray",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Face cream",
        "description": "Face cream",
        "id": 23,
        "responsible_id": 2,
        "category_id": 2,
        "supplier_id": 4,
        "meas_unit": "pc",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Toothpaste",
        "description": "Toothpaste",
        "id": 24,
        "responsible_id": 3,
        "category_id": 2,
        "supplier_id": 4,
        "meas_unit": "pc",
        "min_stock": 1,
        "ord_qty": 1,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Vitamins",
        "description": "Multi-vitamins",
        "id": 25,
        "responsible_id": 1,
        "category_id": 5,
        "supplier_id": 3,
        "meas_unit": "pc",
        "min_stock": 10,
        "ord_qty": 30,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Bandages",
        "description": "Mixed bandages",
        "id": 26,
        "responsible_id": 3,
        "category_id": 5,
        "supplier_id": 4,
        "meas_unit": "pack",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Cat food",
        "description": "Cat food",
        "id": 27,
        "responsible_id": 3,
        "category_id": 7,
        "supplier_id": 2,
        "meas_unit": "bag",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Cat litter",
        "description": "Cat litter",
        "id": 28,
        "responsible_id": 3,
        "category_id": 7,
        "supplier_id": 2,
        "meas_unit": "bag",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Playdough",
        "description": "Playdough",
        "id": 29,
        "responsible_id": 3,
        "category_id": 4,
        "supplier_id": 2,
        "meas_unit": "set",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Bread",
        "description": "Sliced bread",
        "id": 30,
        "responsible_id": 1,
        "category_id": 6,
        "supplier_id": 3,
        "meas_unit": "pc",
        "min_stock": 1,
        "ord_qty": 1,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Oranges",
        "description": "Oranges",
        "id": 31,
        "responsible_id": 3,
        "category_id": 6,
        "supplier_id": 4,
        "meas_unit": "bag",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Bananas",
        "description": "Bananas",
        "id": 32,
        "responsible_id": 3,
        "category_id": 6,
        "supplier_id": 4,
        "meas_unit": "pc",
        "min_stock": 3,
        "ord_qty": 10,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Milk",
        "description": "Milk",
        "id": 33,
        "responsible_id": 1,
        "category_id": 6,
        "supplier_id": 3,
        "meas_unit": "bottle",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Cereals",
        "description": "Cereals",
        "id": 34,
        "responsible_id": 4,
        "category_id": 6,
        "supplier_id": 3,
        "meas_unit": "bag",
        "min_stock": 1,
        "ord_qty": 1,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Chocolate",
        "description": "Chocolate",
        "id": 35,
        "responsible_id": 4,
        "category_id": 6,
        "supplier_id": 3,
        "meas_unit": "pc",
        "min_stock": 1,
        "ord_qty": 2,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Eggs",
        "description": "Eggs",
        "id": 36,
        "responsible_id": 2,
        "category_id": 6,
        "supplier_id": 4,
        "meas_unit": "pc",
        "min_stock": 5,
        "ord_qty": 10,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Pasta",
        "description": "Pasta",
        "id": 37,
        "responsible_id": 2,
        "category_id": 6,
        "supplier_id": 4,
        "meas_unit": "pack",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Coffee",
        "description": "Coffee",
        "id": 38,
        "responsible_id": 1,
        "category_id": 6,
        "supplier_id": 4,
        "meas_unit": "bag",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": True,
        "in_use": True
    },
    {   "name": "Cheese",
        "description": "Cheese",
        "id": 39,
        "responsible_id": 2,
        "category_id": 6,
        "supplier_id": 3,
        "meas_unit": "pc",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Mustard",
        "description": "Mustard",
        "id": 40,
        "responsible_id": 1,
        "category_id": 6,
        "supplier_id": 3,
        "meas_unit": "bottle",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Ketchup",
        "description": "Ketchup",
        "id": 41,
        "responsible_id": 1,
        "category_id": 6,
        "supplier_id": 3,
        "meas_unit": "bottle",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Sunflower oil",
        "description": "Sunflower oil",
        "id": 42,
        "responsible_id": 2,
        "category_id": 6,
        "supplier_id": 4,
        "meas_unit": "bottle",
        "min_stock": 0,
        "ord_qty": 1,
        "to_order": False,
        "critical": False,
        "in_use": True
    },
    {   "name": "Other product",
        "description": "Other product",
        "id": 43,
        "responsible_id": 1,
        "category_id": 3,
        "supplier_id": 2,
        "meas_unit": "pc",
        "min_stock": 1,
        "ord_qty": 2,
        "to_order": False,
        "critical": False,
        "in_use": False
    }
)
# endregion


# region: schedules
@dataclass(frozen=True)
class ValidSchedule:
    """Valid schedule data."""
    name: str = "x"
    type: str = "group"
    elem_id: int = 1
    next_date: date = date.today()
    update_date: date = date.today()+timedelta(days=1)
    update_interval: int = 1
    # Base Schedule / Individual Schedule
    sch_day: int = date.today().isoweekday()
    sch_day_update: int = (date.today() + timedelta(days=1)).isoweekday()
    switch_interval: timedelta = timedelta(weeks=1)
    start_date: date = date.today()
    # Group Schedule
    user_attr: str = User.sat_group.name
    num_groups: int = 2
    first_group: int = 1

test_schedules: tuple[dict[str, str|int|bool]] = (
    {
        "details": "Group schedule",
        "name": str(sat_sch_info.name),
        "type": "group"
    },
    {
        "details": "Individual schedule",
        "name": str(clean_sch_info.name),
        "type": "individual"
    },
)
# endregion
