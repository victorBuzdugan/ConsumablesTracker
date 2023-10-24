"""Guide blueprint."""

from flask import Blueprint, render_template, session, url_for

from helpers import logger, login_required

guide_bp = Blueprint(
    "guide",
    __name__,
    url_prefix="/guide",
    template_folder="templates")

@guide_bp.route("")
@login_required
def guide():
    """"Show guidelines and rules."""
    logger.info("Guide page")
    session["last_url"] = url_for(".guide")
    return render_template("guide/guide.html")
