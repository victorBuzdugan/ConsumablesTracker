"""
Daily tasks.
Note: use only modules from the standard library
"""

import math
import sqlite3
from datetime import date, timedelta
from email.message import EmailMessage
from os import getenv, path
from smtplib import SMTP, SMTPException

from dotenv import load_dotenv
from sqlalchemy import select

from database import Product, User, dbSession
from helpers import CURR_DIR, DB_NAME, logger

load_dotenv()
EMAIL_ACCOUNT = "consumablestracker@gmail.com"
EMAIL_PASSWORD = getenv("EMAIL_PASSW")


def main(db_name: str = DB_NAME) -> None:
    """Run tasks."""
    # daily tasks
    if date.today().day == 1:
        db_backup(db_name, "monthly")
    elif date.today().isoweekday() == 1:
        db_backup(db_name, "weekly")
    else:
        db_backup(db_name, "daily")
    db_reinit(db_name)
    update_schedules(db_name)
    send_users_notif(db_name)
    send_admins_notif()

def db_backup(db_name: str, task: str = "daily") -> None:
    """Backup and vacuum the database.
    
    :param db_name: database that needs to be backed up
    :param task: type of backup (daily, weekly, monthly)
    """
    # pylint: disable=broad-exception-caught
    prod_db = path.join(CURR_DIR, db_name)
    orig_db = path.join(CURR_DIR, path.splitext(db_name)[0] + "_orig.db")
    backup_db = path.join(CURR_DIR, path.splitext(db_name)[0] + "_backup")
    match task:
        case "daily":
            backup_db = backup_db + "_daily.db"
        case "weekly":
            backup_db = backup_db + "_weekly.db"
            logger.debug("Weekly backup")
        case "monthly":
            backup_db = backup_db + "_monthly.db"
            logger.debug("Monthly backup")
        case other:
            logger.error("Backup task argument '%s' invalid", str(other))
            backup_db = backup_db + "_daily.db"
    if path.isfile(orig_db):
        logger.info("No need to backup database as it will be reinitialised")
    else:
        try:
            if not path.isfile(prod_db):
                raise FileNotFoundError("Database doesn't exist")
            source = sqlite3.connect(prod_db)
            if not path.isfile(backup_db):
                logger.debug("Starting first-time backup")
            # sqlite3.connect creates the file if it doesn't exist
            dest = sqlite3.connect(backup_db)
            with source, dest:
                source.backup(dest)
                logger.info("Database backed up")
            dest.close()
        except Exception as err:
            logger.warning("Database could not be backed up")
            logger.debug(err)
        try:
            source.execute("VACUUM")
            logger.info("Production database vacuumed")
            source.close()
        except Exception as err:
            logger.warning("Database could not be vacuumed")
            logger.debug(err)


def db_reinit(db_name: str) -> None:
    """Reinitialise the database from original if it exists.
    
    :param db_name: name of the database that needs to be reinitialised
    """
    # pylint: disable=broad-exception-caught
    prod_db = path.join(CURR_DIR, db_name)
    orig_db = path.join(CURR_DIR, path.splitext(db_name)[0] + "_orig.db")
    if path.isfile(orig_db):
        try:
            source = sqlite3.connect(orig_db)
            if not path.isfile(prod_db):
                raise FileNotFoundError("Database doesn't exist")
            dest = sqlite3.connect(prod_db)
            # reinit db
            with source, dest:
                source.backup(dest)
                logger.info("Database reinitialised")
            source.close()
            dest.close()
        except Exception as err:
            logger.warning("Database could not be reinitialised")
            logger.debug(err)
    else:
        logger.debug("This app doesn't need database reinit")


def update_schedules(db_name: str, base_date: date = date.today()) -> None:
    """Check update_date in schedules and update if necessary.

    :param db_name: name of the database
    :param base_date: date to check against the update date; used for testing
    """
    prod_db = path.join(CURR_DIR, db_name)
    con = sqlite3.connect(prod_db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    schedules = cur.execute("""
        SELECT *
        FROM schedules
        """).fetchall()
    for schedule in schedules:
        update_date = date.fromisoformat(schedule["update_date"])
        if update_date <= base_date:
            # count all the schedules with this name and type
            sch_count = cur.execute("""
                SELECT COUNT(id)
                FROM schedules
                WHERE type = ? AND name = ?
                """, (schedule["type"], schedule["name"])
                ).fetchone()[0]
            next_date = date.fromisoformat(schedule["next_date"])
            sch_interval = (
                timedelta(days=schedule["update_interval"]) * sch_count)
            diff = math.ceil((base_date - next_date).days
                             / sch_interval.days)
            next_date += sch_interval * diff
            update_date += sch_interval * diff
            cur.execute("""
                UPDATE schedules
                SET next_date = ?, update_date = ?
                WHERE id = ?
                """,
                (next_date.isoformat(),
                 update_date.isoformat(),
                 schedule["id"])
                 )
            if schedule["type"] == "group":
                logger.debug("Schedule '%s' group '%d' will be updated",
                            schedule["name"], schedule["elem_id"])
            else:
                user_name = cur.execute("""
                    SELECT name
                    FROM users
                    WHERE id = ?
                    """,
                    (schedule["elem_id"],)).fetchone()[0]
                logger.debug("Schedule '%s' user '%s' will be updated",
                            schedule["name"], user_name)
    if con.in_transaction:
        con.commit()
        if con.total_changes == 1:
            logger.info("%d schedule updated", con.total_changes)
        else:
            logger.info("%d schedules updated", con.total_changes)
    else:
        logger.info("No need to update schedules")
    con.close()


def send_users_notif(db_name: str) -> None:
    """Check users status and, if required, send a notification email.

    :param db_name: name of the database
    """
    prod_db = path.join(CURR_DIR, db_name)
    con = sqlite3.connect(prod_db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    if notif_users := cur.execute("""
                                  SELECT name, email
                                  FROM users
                                  WHERE email != ''
                                    AND in_use = True
                                    AND done_inv = False
                                    AND reg_req = False
                                  """).fetchall():
        try:
            with SMTP(host="smtp.gmail.com", port=587) as server:
                server.starttls()
                server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
                for user in notif_users:
                    msg = EmailMessage()
                    msg["From"] = EMAIL_ACCOUNT
                    msg["To"] = user["email"]
                    msg["Subject"] = "ConsumablesTracker - Reminder"
                    msg.set_content(f"Hi {user['name']},\n" +
                                    "Don't forget to check the inventory!")
                    msg.add_alternative(f"""
                        <html>
                        <body>
                            <p>Hi <b>{user["name"]}</b>,</p>
                            <p>Don't forget to <b>check the inventory</b>!</p>
                        </body>
                        </html>""",
                        subtype='html')
                    server.send_message(msg)
                    logger.debug("Sent user email notification to '%s'",
                                 user["name"])
        except SMTPException as e:
            logger.warning(str(e))
    else:
        logger.debug("No user notification need to be sent")


def send_admins_notif() -> None:
    """Check app status and, if required, send a notification email to admins.

    :param db_name: name of the database
    """
    with dbSession() as db_session:
        notif_admins = db_session.scalars(
            select(User)
            .filter_by(admin=True, in_use=True)
            .filter(User.email != "")
        ).all()
    if notif_admins:
        notifications = []
        with dbSession() as db_session:
            if db_session.scalar(select(User).filter_by(done_inv=False)):
                notifications.append(
                    "there are users that have to check the inventory")
            if db_session.scalar(select(User).filter_by(reg_req=True)):
                notifications.append(
                    "there are users that need registration approval")
            if db_session.scalar(select(User).filter_by(req_inv=True)):
                notifications.append(
                    "there are users that requested inventorying")
            if db_session.scalar(select(Product).filter_by(to_order=True)):
                notifications.append(
                    "there are products that need to be ordered")
        if notifications:
            try:
                with SMTP(host="smtp.gmail.com", port=587) as server:
                    server.starttls()
                    server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
                    for admin in notif_admins:
                        msg = EmailMessage()
                        msg["From"] = EMAIL_ACCOUNT
                        msg["To"] = admin.email
                        msg["Subject"] = "ConsumablesTracker - Notifications"
                        msg.set_content(f"Hi {admin.name},\n" +
                                        "These are the daily notifications:\n" +
                                        "- " +
                                        "\n- ".join(notifications))
                        msg.add_alternative(f"""
                            <html>
                            <body>
                                <p>Hi <b>{admin.name}</b>,</p>
                                <p>These are the <b>daily notifications</b>:</p>
                                <ul>
                                    <li>{"</li> <li>".join(notifications)}</li>
                                </ul>
                            </body>
                            </html>""",
                            subtype='html')
                        server.send_message(msg)
                        logger.debug("Sent admin email notification to '%s'",
                                 admin.name)
            except SMTPException as e:
                print(e)
                logger.warning(str(e))
        else:
            logger.debug("No admin notification need to be sent")
    else:
        logger.debug("No eligible admin found to send admin notification")



if __name__== "__main__":   # pragma: no cover
    main()
