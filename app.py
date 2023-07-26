from datetime import datetime

from flask import Flask

from blueprints.auth.auth import auth_bp
from blueprints.cat.cat import cat_bp
from blueprints.inv.inv import inv_bp
from blueprints.main.main import main_bp
from blueprints.sup.sup import sup_bp
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
app.register_blueprint(cat_bp)
app.register_blueprint(sup_bp)
