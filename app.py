import sqlite3

from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)


app = Flask(__name__)

app.config.from_prefixed_env()

DATABASE = "inventory.db"

@app.route("/")
def index():
    """Index page"""
    return "Hello world!"


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page"""
    session["username"] = request.form["username"]
    return redirect(url_for("index"))
    return "Please login to website"


@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("Succesfully logged out")
    return redirect(url_for("index"))





if __name__ == "__main--":
    # with app.test_request_context():
    #     print(url_for("index"))
    #     print(url_for("login"))
    pass
