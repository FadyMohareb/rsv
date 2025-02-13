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
from sqlalchemy.exc import IntegrityError

from project import app, db, User, Distribution, Organization


cli = FlaskGroup(app)


@cli.command("create_db")
def create_db():
    db.drop_all()
    db.create_all()
    db.session.commit()


@cli.command("seed_db")
def seed_db():
    base_dir = "data/"

    try:
        org_dict = {}
    
        # Iterate over distribution directories in base_dir
        for dist_folder in os.listdir(base_dir):
            dist_path = os.path.join(base_dir, dist_folder)
            if not os.path.isdir(dist_path):
                continue  # skip files
            
            distribution_name = dist_folder  # Use folder name as distribution name
            all_samples = []      # To collect sample names
            orgs_for_distribution = []  # To collect Organization objects for this distribution
            
            # Iterate over organization directories in the distribution folder
            for org_folder in os.listdir(dist_path):
                org_path = os.path.join(dist_path, org_folder)
                if not os.path.isdir(org_path):
                    continue
                
                organization_name = org_folder  # Folder name as organization name
                # If organization not created yet, create and store it
                if organization_name not in org_dict:
                    org_obj = Organization(name=organization_name)
                    db.session.add(org_obj)
                    db.session.flush()  # Ensure an ID is assigned
                    org_dict[organization_name] = org_obj
                else:
                    org_obj = org_dict[organization_name]
                
                orgs_for_distribution.append(org_obj)
                
                # Iterate over sample directories inside the organization folder
                for sample_folder in os.listdir(org_path):
                    sample_path = os.path.join(org_path, sample_folder)
                    if os.path.isdir(sample_path):
                        all_samples.append(sample_folder)
            
            # Create and add the Distribution with its organizations and samples
            distribution = Distribution(
                name=distribution_name,
                samples=list(set(all_samples)),
                organizations=orgs_for_distribution
            )
            db.session.add(distribution)

        # Add users
        db.session.add(User(email="elon@gmail.com", username="elonmusk", password=generate_password_hash("passwordtesla"), role="superuser", organization=org_dict.get("9999")))
        db.session.add(User(email="bill@gmail.com", username="bill", password=generate_password_hash("password1"),  organization=org_dict.get("WR099")))
        db.session.add(User(email="jill@gmail.com", username="jill", password=generate_password_hash("password2"),  organization=org_dict.get("WR090")))
        db.session.add(User(email="testOrg@gmail.com", username="testOrg", password=generate_password_hash("testOrg"),  organization=org_dict.get("testOrg"), role="superuser"))
        db.session.add(User(email="testUser@gmail.com", username="testUser", password=generate_password_hash("testUser"),  organization=org_dict.get("testOrg")))
        db.session.commit()

        # Query the user with username "elonmusk"
        user = User.query.filter_by(username="elonmusk").first()

        # Check samples JSON for distros
        print("\n\033[92mDatabase seeding succeeded\033[0m\n")
    except IntegrityError as e:
        print("\n\033[91mIntegrityError happened, most likely because databases are already seeded, it is not an issue nor a bug. \033[0m\n")


@cli.command("run_worker")
def run_worker():
    redis_connection = redis.from_url(app.config["REDIS_URL"])
    with Connection(redis_connection):
        worker = Worker(app.config["QUEUES"])
        worker.work()


if __name__ == "__main__":
    cli()
