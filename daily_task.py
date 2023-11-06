"""Daily tasks."""
# pylint: disable=broad-exception-caught

import math
import sqlite3
from datetime import date, timedelta
from os import getenv, path, remove
from smtplib import SMTPAuthenticationError, SMTPException
from typing import Callable

from flask import render_template
from flask_mail import Message
from sqlalchemy import func, select

from app import app, mail
from database import Product, Schedule, User, dbSession
from helpers import DB_NAME, logger

func: Callable


def main() -> None:
    """Run daily tasks."""
    db_backup()
    db_reinit()
    update_schedules()
    send_users_notif()
    send_admins_notif()
    send_log()


def db_backup_name(prod_db: str) -> str:
    """Get backup db name based on date."""
    if date.today().day == 1:
        backup_db = path.splitext(prod_db)[0] + "_backup_monthly.db"
        logger.debug("Monthly backup")
    elif date.today().isoweekday() == 1:
        backup_db = path.splitext(prod_db)[0] + "_backup_weekly.db"
        logger.debug("Weekly backup")
    else:
        backup_db = path.splitext(prod_db)[0] + "_backup_daily.db"
    return backup_db


def db_backup() -> None:
    """Backup and vacuum the database."""
    prod_db = dbSession.kw["bind"].url.database # pylint: disable=no-member
    orig_db = path.splitext(prod_db)[0] + "_orig.db"
    if path.isfile(orig_db):
        logger.info("No need to backup database as it will be reinitialised")
        return
    backup_db = db_backup_name(prod_db)
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


def db_reinit() -> None:
    """Reinitialise the database from original if it exists."""
    prod_db = dbSession.kw["bind"].url.database # pylint: disable=no-member
    orig_db = path.splitext(prod_db)[0] + "_orig.db"
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


def update_schedules() -> None:
    """Check update_date in schedules and update if necessary.

    :param base_date: date to check against the update date; used for testing
    """
    with dbSession() as db_session:
        schedules = db_session.scalars(
            select(Schedule)
            .filter(Schedule.update_date <= date.today())
        ).all()
        if not schedules:
            logger.info("No need to update schedules")
            return
        for schedule in schedules:
            # count all the schedules with this name and type
            sch_count = db_session.scalar(
                select(func.count(Schedule.id))
                .filter_by(type=schedule.type, name=schedule.name))
            sch_increment = timedelta(
                days=schedule.update_interval * sch_count)
            diff = math.ceil(
                (date.today() - schedule.next_date).days / sch_increment.days)
            schedule.next_date += sch_increment * diff
            schedule.update_date += sch_increment * diff
            if schedule.type == "group":
                logger.debug("Schedule '%s' group '%d' will be updated",
                            schedule.name, schedule.elem_id)
            else:
                logger.debug("Schedule '%s' user '%s' will be updated",
                            schedule.name,
                            db_session.get(User, schedule.elem_id).name)
        db_session.commit()
        if len(schedules) == 1:
            logger.info("1 schedule updated")
        else:
            logger.info("%d schedules updated", len(schedules))


def send_users_notif() -> None:
    """Check users status and, if required, send a notification email."""
    if date.today().isocalendar().weekday in {6, 7}:
        logger.debug("No user notifications will be sent (weekend)")
        return
    with dbSession() as db_session:
        eligible_users = db_session.scalars(
            select(User)
            .filter_by(in_use=True, done_inv=False, reg_req=False)
            .filter(User.email != "")
        ).all()
    if eligible_users:
        try:
            with app.app_context(), mail.connect() as conn:
                for user in eligible_users:
                    msg = Message(
                            subject="ConsumablesTracker - Reminder",
                            recipients=[user.email])
                    msg.body = render_template("mail/user_notif.plain",
                                                   username=user.name)
                    msg.html = render_template("mail/user_notif.html",
                                                   username=user.name)
                    conn.send(msg)
                    logger.debug("Sent user email notification to '%s'",
                                 user.name)
        except SMTPAuthenticationError:
            logger.warning("Failed email SMTP authentication")
        except SMTPException as err:
            logger.warning(str(err))
    else:
        logger.debug("No eligible user found to send notification")


def send_admins_notif() -> None:
    """Check status and, if required, send a notification email to admins."""
    if date.today().isocalendar().weekday in {6, 7}:
        logger.debug("No admin notifications will be sent (weekend)")
        return
    with dbSession() as db_session:
        eligible_admins = db_session.scalars(
            select(User)
            .filter_by(admin=True, in_use=True)
            .filter(User.email != "")
        ).all()
    if eligible_admins:
        notifications = []
        with dbSession() as db_session:
            if db_session.scalar(select(User).filter_by(reg_req=True)):
                notifications.append(
                    "there are users that need registration approval")
            if db_session.scalar(select(User).filter_by(req_inv=True)):
                notifications.append(
                    "there are users that requested inventorying")
            if db_session.scalar(select(User).filter_by(done_inv=False)):
                notifications.append(
                    "there are users that have to check the inventory")
            if db_session.scalar(select(Product).filter_by(to_order=True)):
                notifications.append(
                    "there are products that need to be ordered")
        if notifications:
            try:
                with app.app_context(), mail.connect() as conn:
                    for admin in eligible_admins:
                        msg = Message(
                            subject="ConsumablesTracker - Notifications",
                            recipients=[admin.email])
                        msg.body = render_template("mail/admin_notif.plain",
                                                   username=admin.name,
                                                   notifications=notifications)
                        msg.html = render_template("mail/admin_notif.html",
                                                   username=admin.name,
                                                   notifications=notifications)
                        conn.send(msg)
                        logger.debug("Sent admin email notification to '%s'",
                                 admin.name)
            except SMTPAuthenticationError:
                logger.warning("Failed email SMTP authentication")
            except SMTPException as err:
                logger.warning(str(err))
        else:
            logger.debug("No admin notifications need to be sent")
    else:
        logger.debug("No eligible admin found to send notification")


def send_log() -> None:
    """Send log file."""
    recipient = getenv("ADMIN_EMAIL")
    log_file = logger.handlers[0].baseFilename
    daily_log = path.splitext(log_file)[0] + "_daily.log"
    if recipient and path.isfile(log_file):
        # filter records from yesterday to today
        yesterday = date.today() - timedelta(days=1)
        with open(file=log_file, mode="r", encoding="UTF-8") as log:
            with open(file=daily_log, mode="w", encoding="UTF-8") as temp_log:
                for record in log:
                    if (record.startswith(yesterday.strftime("%d.%m")) or
                            record.startswith(date.today().strftime("%d.%m"))):
                        temp_log.write(record)
        try:
            with app.app_context(), mail.connect() as conn:
                msg = Message(recipients=[recipient])
                msg.subject = ("ConsumablesTracker - LogFile - " +
                               DB_NAME.rstrip('.db'))
                msg.body = "Log file attached."
                msg.html = "<p>Log file attached.</p>"
                with app.open_resource(daily_log) as log:
                    msg.attach(
                        filename="daily_log.log",
                        content_type="text/plain",
                        data=log.read())
                conn.send(msg)
                logger.debug("Sent log file to '%s'", recipient)
        except SMTPAuthenticationError:
            logger.warning("Failed email SMTP authentication")
        except SMTPException as err:
            logger.warning(str(err))
        finally:
            remove(daily_log)
    else:
        logger.warning("No recipient or no log file to send")


if __name__== "__main__":   # pragma: no cover
    main()
