import os
import click
from flask.cli import FlaskGroup
from threading import Thread
import time
import redis
from rq import Worker, Queue, Connection
from rq_scheduler import Scheduler
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash

from project import app, db, User, Distribution, Organization


cli = FlaskGroup(app)


@cli.command("create_db")
def create_db():
    db.drop_all()
    db.create_all()
    db.session.commit()


@cli.command("seed_db")
def seed_db():
    # Clear the database to avoid duplicate entries
    db.session.query(Organization).delete()
    db.session.query(Distribution).delete()

    # Add Organizations
    org1 = Organization(name="WR099")
    org2 = Organization(name="WR006")
    org3 = Organization(name="WR024")
    org4 = Organization(name="9999")
    org5 = Organization(name="testOrg")
    org6 = Organization(name="WR090")
    orgList=[org1, org2, org3, org4, org5, org6]
    db.session.add_all(orgList)
    db.session.flush()  # Ensure IDs are assigned to organizations

    # Add Distributions
    db.session.add(Distribution(name="RSV 2024 Winter", samples=["2524", "2525", "2526"], organizations=orgList))

    # Add users
    db.session.add(User(email="elon@gmail.com", username="elonmusk", password=generate_password_hash("passwordtesla"), role="superuser", organization=org4))
    db.session.add(User(email="bill@gmail.com", username="bill", password=generate_password_hash("password1"),  organization=org1))
    db.session.add(User(email="jill@gmail.com", username="jill", password=generate_password_hash("password2"),  organization=org2))
    db.session.add(User(email="joe@gmail.com", username="joe", password=generate_password_hash("password3"),  organization=org3))
    db.session.add(User(email="testOrg@gmail.com", username="testOrg", password=generate_password_hash("testOrg"),  organization=org5, role="superuser"))
    db.session.add(User(email="testUser@gmail.com", username="testUser", password=generate_password_hash("testUser"),  organization=org5))
    db.session.add(User(email="WR090@gmail.com", username="WR090", password=generate_password_hash("WR090"),  organization=org6))
    print("sanity check")
    db.session.commit()

    # Query the user with username "elonmusk"
    user = User.query.filter_by(username="elonmusk").first()
    print(user.password)  # Optional: Print the found user to verify
    print(type(user))

    # Check samples JSON for distros
    print(db.session.query(Distribution).all())


@cli.command("run_worker")
def run_worker():
    redis_connection = redis.from_url(app.config["REDIS_URL"])
    with Connection(redis_connection):
        worker = Worker(app.config["QUEUES"])
        worker.work()


if __name__ == "__main__":
    cli()
