"""UI Messages"""

from flask_babel import lazy_gettext as lg

from constants import Constant


class Message:
    """UI messages"""
    class Login:
        """Login messages"""
        LoginReq = {"message": lg("You have to be logged in..."),
                       "category": "warning"}

pass
