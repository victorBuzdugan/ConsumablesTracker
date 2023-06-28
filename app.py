from datetime import datetime

from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)

from database import dbSession, User, Category, Supplier, Product
from blueprints.auth.auth import auth_bp
from blueprints.main.main import main_bp
from helpers import admin_required, login_required

app = Flask(__name__)

app.config.from_prefixed_env()

# jinja date time
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)

# @app.route("/")
# @login_required
# def index():
#     """Index page."""
#     return render_template("index.html")


# with app.test_request_context():
#     print(app.url_map)
#     print(url_for("index"))
#     print(url_for("login"))
