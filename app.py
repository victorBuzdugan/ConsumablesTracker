from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)

from database import dbSession, User, Category, Supplier, Product
from blueprints.auth.auth import auth_bp
from helpers import admin_required, login_required

app = Flask(__name__)

app.config.from_prefixed_env()

app.register_blueprint(auth_bp)


@app.route("/")
@login_required
def index():
    """Index page."""
    return render_template("index.html")


# with app.test_request_context():
#     print(app.url_map)
#     print(url_for("index"))
#     print(url_for("login"))
