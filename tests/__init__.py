"""Tests constants."""

from dataclasses import dataclass
from os import getenv, path

from daily_task import db_backup_name
from database import User
from helpers import CURR_DIR, DB_NAME

TEST_DB_NAME = "." + DB_NAME

PROD_DB = path.join(CURR_DIR, TEST_DB_NAME)
BACKUP_DB = db_backup_name(PROD_DB)
ORIG_DB = path.join(CURR_DIR, path.splitext(TEST_DB_NAME)[0] + "_orig.db")
TEMP_DB = path.join(CURR_DIR, path.splitext(TEST_DB_NAME)[0] + "_temp.db")

@dataclass(frozen=True)
class ValidUser:
    """Valid user data."""
    name: str = "valid_name"
    password: str = "P@ssw0rd"
    email: str = "email@example.com"


test_users: tuple[dict[str, str|bool|int]] = (
    {"name": "Admin",
    "password": getenv("ADMIN_PASSW"),
    "admin": True,
    "in_use": False,
    "done_inv": True,
    "reg_req": False,
    "req_inv": False,
    "details": "Hidden admin",
    "email": "",
    "sat_group": 1,
    },
    {"name": "user1",
    "password": "Q!111111",
    "admin": True,
    "in_use": True,
    "done_inv": True,
    "reg_req": False,
    "req_inv": False,
    "details": "",
    "email": "consumablestracker+user1@gmail.com",
    "sat_group": 1
    },
    {"name": "user2",
    "password": "Q!222222",
    "admin": True,
    "in_use": True,
    "done_inv": True,
    "reg_req": False,
    "req_inv": False,
    "details": "",
    "email": "consumablestracker+user2@gmail.com",
    "sat_group": 2
    },
    {"name": "user3",
    "password": "Q!333333",
    "admin": False,
    "in_use": True,
    "done_inv": True,
    "reg_req": False,
    "req_inv": False,
    "details": "",
    "email": "consumablestracker+user3@gmail.com",
    "sat_group": 1
    },
    {"name": "user4",
    "password": "Q!444444",
    "admin": False,
    "in_use": True,
    "done_inv": True,
    "reg_req": False,
    "req_inv": False,
    "details": "",
    "email": "consumablestracker+user4@gmail.com",
    "sat_group": 2
    },
    {"name": "user5",
    "password": "Q!555555",
    "admin": False,
    "in_use": True,
    "done_inv": True,
    "reg_req": True,
    "req_inv": False,
    "details": "",
    "email": "consumablestracker+user5@gmail.com",
    "sat_group": 1
    },
    {"name": "user6",
    "password": "Q!666666",
    "admin": False,
    "in_use": False,
    "done_inv": True,
    "reg_req": False,
    "req_inv": False,
    "details": "",
    "email": "consumablestracker+user6@gmail.com",
    "sat_group": 1
    },
    {"name": "user7",
    "password": "Q!777777",
    "admin": False,
    "in_use": True,
    "done_inv": True,
    "reg_req": False,
    "req_inv": False,
    "details": "",
    "email": "",
    "sat_group": 1
    },
    )
