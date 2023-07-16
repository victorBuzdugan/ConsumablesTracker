from datetime import datetime

from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)

from database import dbSession, User, Category, Supplier, Product
from blueprints.auth.auth import auth_bp
from blueprints.main.main import main_bp
from blueprints.inv.inv import inv_bp
from blueprints.users.users import users_bp

app = Flask(__name__)

app.config.from_prefixed_env()

# jinja date time
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(inv_bp)
app.register_blueprint(users_bp)
