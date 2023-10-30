"""Main app."""

from datetime import datetime
from typing import Literal

from flask import Flask, flash, redirect, request, session
from flask_babel import Babel, gettext
from flask_mail import Mail

from blueprints.auth.auth import auth_bp
from blueprints.cat.cat import cat_bp
from blueprints.guide.guide import guide_bp
from blueprints.inv.inv import inv_bp
from blueprints.main.main import main_bp
from blueprints.prod.prod import prod_bp
from blueprints.sch.sch import sch_bp
from blueprints.sup.sup import sup_bp
from blueprints.users.users import users_bp
from helpers import logger

LANGUAGES = ("ro", "en")

def get_locale() -> Literal["ro", "en"]:
    """Set the language the page will be displayed."""
    if language := session.get("language"):
        return language
    # try to guess the language from the user accept header browser
    if language := request.accept_languages.best_match(LANGUAGES):
        logger.info("Got locale language '%s'", language)
    else:
        logger.warning("Could not get locale language")
        language = "en"
    session["language"] = language
    return language

app = Flask(__name__)

app.config.from_prefixed_env()

babel = Babel(app, locale_selector=get_locale)

mail = Mail(app)


@app.context_processor
def inject_now():
    """Function for jinja date time"""
    return {'now': datetime.utcnow()}


app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(inv_bp)
app.register_blueprint(users_bp)
app.register_blueprint(cat_bp)
app.register_blueprint(sup_bp)
app.register_blueprint(prod_bp)
app.register_blueprint(guide_bp)
app.register_blueprint(sch_bp)


@app.route("/language/<language>")
def set_language(language: str = "en"):
    """Change app display language."""
    if language in LANGUAGES:
        session["language"] = language
    else:
        session["language"] = "en"
    logger.info("Language changed to '%s'", language)
    flash(gettext("Language changed"))
    if request.referrer:
        return redirect(request.referrer)
    return redirect("/")
