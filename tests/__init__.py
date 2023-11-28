"""Tests constants and helpers."""

from dataclasses import dataclass
from os import getenv
from pathlib import Path

from werkzeug.test import TestResponse

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
    try:
        assert len(response.history) == total_redirects
        for num in range(total_redirects):
            assert response.history[num].status_code == 302
        assert response.status_code == 200
        assert response.request.path == final_url
    except AssertionError:
        return False
    return True
# endregion


# region: users
@dataclass(frozen=True)
class ValidUser:
    """Valid user data."""
    name: str = "x" * Constant.User.Name.min_length
    password: str = "P@ssw0rd"
    email: str = "email@example.com"

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

test_users: tuple[dict[str, str|bool|int]] = (
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

test_categories: tuple[dict[str, str|bool]] = (
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
        "details": "Retired category",
        "id": 8,
        "name": "Others",
        "in_use": False,
        "has_products": False,
    },
)
# endregion
