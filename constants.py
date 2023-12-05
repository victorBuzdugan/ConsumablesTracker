"""App constants."""

import re
from os import path


class Constant:
    """App constants."""
    class Basic:
        """Basic constants"""
        current_dir = path.dirname(path.realpath(__file__))
        db_name = "inventory.db"
    class User:
        """User related constants"""
        class Name:
            """User name constants"""
            min_length = 3
            max_length = 15
        class Password:
            """Password constants"""
            min_length = 8
            regex = re.compile(r"(?=.*\d)(?=.*[A-Z])(?=.*[!@#$%^&*_=+]).{8,}")
            symbols = "!@#$%^&*_=+"
    class Category:
        """Category related constants"""
        class Name:
            """Category name constants"""
            min_length = 3
    class Supplier:
        """Supplier related constants"""
        class Name:
            """Supplier name constants"""
            min_length = 3
    class Product:
        """Product related constants"""
        class Name:
            """Product name constants"""
            min_length = 3
            max_length = 15
        class Description:
            """Product description constants"""
            min_length = 3
            max_length = 50
        class MinStock:
            """Product minimum stock constants"""
            min_value = 0
        class OrdQty:
            """Product order quantity constants"""
            min_value = 1
    class SQLite:
        """Database constants"""
        class Int:
            """Integer limits"""
            max_value = 9223372036854775807
