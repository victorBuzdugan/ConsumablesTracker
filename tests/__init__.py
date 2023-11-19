"""Tests constants."""

from dataclasses import dataclass
from os import getenv, path

from daily_task import db_backup_name
from database import User
from helpers import Constants

TEST_DB_NAME = "." + Constants.Basic.db_name

PROD_DB = path.join(Constants.Basic.current_dir, TEST_DB_NAME)
BACKUP_DB = db_backup_name(PROD_DB)
ORIG_DB = path.join(Constants.Basic.current_dir,
                    path.splitext(TEST_DB_NAME)[0] + "_orig.db")
TEMP_DB = path.join(Constants.Basic.current_dir,
                    path.splitext(TEST_DB_NAME)[0] + "_temp.db")

@dataclass(frozen=True)
class ValidUser:
    """Valid user data."""
    name: str = "x" * Constants.User.Name.min_length
    password: str = "P@ssw0rd"
    email: str = "email@example.com"

@dataclass(frozen=True)
class InvalidUser:
    """Invalid user data."""
    short_name: str = "x" * (Constants.User.Name.min_length - 1)
    long_name: str = "x" * (Constants.User.Name.max_length + 1)
    short_password: str = "x" * (Constants.User.Password.min_length - 1)
    only_lowercase_password: str = "x" * Constants.User.Password.min_length
    no_special_char_password: str = ("X1" +
                                     "x" * Constants.User.Password.min_length)
    no_uppercase_password: str = ("#1" +
                                  "x" * Constants.User.Password.min_length)
    no_number_password: str = ("#X" +
                               "x" * Constants.User.Password.min_length)

@dataclass(frozen=True)
class ValidCategory:
    """Valid category data."""
    name: str = "valid_name"
    in_use: str = "on"


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
    },
    {
        "details": "Admin user with products",
        "sat_group": 1,
        "name": "user1",
        "password": "Q!111111",
        "admin": True,
        "in_use": True,
        "done_inv": True,
        "reg_req": False,
        "req_inv": False,
        "email": "consumablestracker+user1@gmail.com",
        "id": 1,
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
    },
)


test_categories: tuple[dict[str, str|bool]] = (
    {"name": "Household",
     "in_use": True,
     "description": "Household consumables"},
    {"name": "Personal",
     "in_use": True,
     "description": "Personal consumables"},
    {"name": "Electronics",
     "in_use": True,
     "description": ""},
    {"name": "Kids",
     "in_use": True,
     "description": ""},
    {"name": "Health",
     "in_use": True,
     "description": ""},
    {"name": "Groceries",
     "in_use": True,
     "description": ""},
    {"name": "Pets",
     "in_use": True,
     "description": ""},
    {"name": "Others",
     "in_use": False,
     "description": ""},
)

test_categories_with_products = test_categories[:6]
