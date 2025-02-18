from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()

class User(db.Model):
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
        self.email = email
        self.username = username
        self.organization_id = organization.id
        self.password = password
        self.role = role
    def __repr__(self):
        return "%s/%s/%s/%s" % ( self.id, self.password, self.role, self.organization_id)
    def is_active(self):
        return True
    def is_superuser(self):
        return self.role == "superuser"


# Association table for many-to-many relationship between distributions and organizations
distribution_organization = db.Table(
    'distribution_organization',
    db.Column('distribution_id', db.Integer, db.ForeignKey('distributions.id'), primary_key=True),
    db.Column('organization_id', db.Integer, db.ForeignKey('organizations.id'), primary_key=True)
)

class Organization(db.Model):
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
        return f"<Organization(id={self.id}, name={self.name})>"
    
class Distribution(db.Model):
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
        # For clarity, list organization names in the representation
        org_names = [org.name for org in self.organizations] if self.organizations else []
        return f"<Distribution(id={self.id}, name={self.name}, samples={self.samples}, organizations={org_names})>"

    

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_email = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_dismissed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_email": self.user_email,
            "message": self.message,
            "is_dismissed": self.is_dismissed,
            "created_at": self.created_at.isoformat(),
        }    
    
class Submission(db.Model):
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
        return (f"<Submission(id={self.id}, user_id={self.user_id}, "
                f"organization_id={self.organization_id}, distribution_id={self.distribution_id}, "
                f"sample={self.sample}, sequencing_type={self.sequencing_type}, "
                f"submission_date={self.submission_date})>")
