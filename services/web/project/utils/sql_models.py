"""
sql_models.py
=============

This module defines the database models for the application using SQLAlchemy.
It includes models for Users, Organizations, Distributions, Notifications, and Submissions.
The models are designed to work with the PostgreSQL database service (including JSON support).

Models:
    User: Represents a user in the system.
    Organization: Represents an organization that users belong to.
    Distribution: Represents a distribution containing samples and associated organizations.
    Notification: Represents a notification sent to users.
    Submission: Represents a sample submission with associated sequencing data.

:author: Kevin
:version: 1.0
:date: 2025-02-21
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()

class User(db.Model):
    """
    User model representing an application user.

    Attributes:
        id (int): Primary key.
        email (str): Unique email address of the user.
        username (str): Username for the user.
        role (str): Role of the user (e.g., "user", "superuser").
        organization_id (int): Foreign key linking the user to an Organization.
        password (str): Hashed password.
        active (bool): Flag indicating if the user is active.
        organization (Organization): The Organization object associated with the user.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    username = db.Column(db.String(128), unique=False, nullable=False)
    role = db.Column(db.String(15), unique=False, nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)  # Foreign key
    password = db.Column(db.String(256), unique=False, nullable=False)
    active = db.Column(db.Boolean(), default=True, nullable=False)

    # Relationship to Organization
    organization = db.relationship("Organization", back_populates="users")

    def __init__(self, email, username, organization, password, role="user"):
        """
        Initialize a new User instance.

        :param email: The user's email.
        :type email: str
        :param username: The username.
        :type username: str
        :param organization: An Organization object the user belongs to.
        :type organization: Organization
        :param password: The user's password (should be hashed).
        :type password: str
        :param role: The role of the user (default "user").
        :type role: str
        """
        self.email = email
        self.username = username
        self.organization_id = organization.id
        self.password = password
        self.role = role
    def __repr__(self):
        """
        Return a string representation of the User.

        :return: A string in the format "id/password/role/organization_id".
        :rtype: str
        """
        return "%s/%s/%s/%s" % ( self.id, self.password, self.role, self.organization_id)
    def is_active(self):
        """
        Check if the user is active.

        :return: True, indicating the user is active.
        :rtype: bool
        """
        return True
    def is_superuser(self):
        """
        Check if the user has superuser privileges.

        :return: True if the user's role is 'superuser', otherwise False.
        :rtype: bool
        """
        return self.role == "superuser"


# Association table for many-to-many relationship between distributions and organizations
distribution_organization = db.Table(
    'distribution_organization',
    db.Column('distribution_id', db.Integer, db.ForeignKey('distributions.id'), primary_key=True),
    db.Column('organization_id', db.Integer, db.ForeignKey('organizations.id'), primary_key=True)
)

class Organization(db.Model):
    """
    Organization model representing an organization in the system.

    Attributes:
        id (int): Primary key.
        name (str): Unique name of the organization.
        users (list[User]): List of User objects associated with this organization.
        distributions (list[Distribution]): List of Distribution objects linked via a many-to-many relationship.
    """
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    # Relationship with User
    users = db.relationship("User", back_populates="organization", cascade="all, delete-orphan")

    # Add the reciprocal relationship to Distribution
    distributions = db.relationship(
        "Distribution",
        secondary=distribution_organization,
        back_populates="organizations"
    )

    def __repr__(self):
        """
        Return a string representation of the Organization.

        :return: A string in the format "<Organization(id, name)>".
        :rtype: str
        """
        return f"<Organization(id={self.id}, name={self.name})>"
    
class Distribution(db.Model):
    """
    Distribution model representing a distribution of samples.

    Attributes:
        id (int): Primary key.
        name (str): Unique name of the distribution.
        created_at (datetime): Timestamp when the distribution was created.
        samples (JSON): A JSON field storing a list of sample names.
        organizations (list[Organization]): Organizations associated with this distribution.
    """
    __tablename__ = "distributions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    samples = db.Column(JSON, nullable=True)  # Store list of sample names as JSON

    # Add relationship to Organization via the association table
    organizations = db.relationship(
        "Organization",
        secondary=distribution_organization,
        back_populates="distributions"
    )

    def __repr__(self):
        """
        Return a string representation of the Distribution.

        Includes the distribution ID, name, sample list, and names of associated organizations.

        :return: A string representation.
        :rtype: str
        """
        # For clarity, list organization names in the representation
        org_names = [org.name for org in self.organizations] if self.organizations else []
        return f"<Distribution(id={self.id}, name={self.name}, samples={self.samples}, organizations={org_names})>"

    

class Notification(db.Model):
    """
    Notification model representing a notification for a user.

    Attributes:
        id (int): Primary key (autoincremented).
        user_email (str): Email of the user receiving the notification.
        message (str): The notification message.
        is_dismissed (bool): Flag indicating if the notification has been dismissed.
        created_at (datetime): Timestamp when the notification was created.
    """
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_email = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_dismissed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """
        Convert the Notification instance to a dictionary.

        :return: A dictionary representation of the notification.
        :rtype: dict
        """
        return {
            "id": self.id,
            "user_email": self.user_email,
            "message": self.message,
            "is_dismissed": self.is_dismissed,
            "created_at": self.created_at.isoformat(),
        }    
    
class Submission(db.Model):
    """
    Submission model representing a sample submission.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key referencing the User.
        organization_id (int): Foreign key referencing the Organization.
        distribution_id (int): Foreign key referencing the Distribution.
        sample (str): The identifier of the submitted sample.
        sequencing_type (str): Type of sequencing performed.
        submission_date (datetime): Date and time of the submission.
        user (User): Relationship to the User.
        organization (Organization): Relationship to the Organization.
        distribution (Distribution): Relationship to the Distribution.
    """
    __tablename__ = "submissions"

    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    distribution_id = db.Column(db.Integer, db.ForeignKey('distributions.id'), nullable=False)
    
    # The sample from the distribution that was submitted (as a string identifier)
    sample = db.Column(db.String(128), nullable=False)
    
    # Additional info
    sequencing_type = db.Column(db.String(64), nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.now, nullable=False)

    # Relationships for convenient access to associated objects
    user = db.relationship("User", backref=db.backref("submissions", lazy=True))
    organization = db.relationship("Organization", backref=db.backref("submissions", lazy=True))
    distribution = db.relationship("Distribution", backref=db.backref("submissions", lazy=True))

    def __repr__(self):
        """
        Return a string representation of the Submission.

        :return: A string summarizing key fields of the submission.
        :rtype: str
        """
        return (f"<Submission(id={self.id}, user_id={self.user_id}, "
                f"organization_id={self.organization_id}, distribution_id={self.distribution_id}, "
                f"sample={self.sample}, sequencing_type={self.sequencing_type}, "
                f"submission_date={self.submission_date})>")
