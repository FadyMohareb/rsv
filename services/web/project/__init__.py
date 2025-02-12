from flask import Flask, jsonify, send_from_directory, send_file, Response, render_template, request, url_for, redirect, session, abort
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user 

import os, subprocess, json, gzip, shutil
from sqlalchemy.orm.attributes import flag_modified
from flask_wtf import Form
from functools import wraps
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_cors import CORS
import flask
from project.utils.report_parser import process_all_reports
from project.utils.docx import generate_docx_report
import plotly.graph_objs as go
import plotly.io as pio
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
import redis
from rq import Queue, Connection
from flask import render_template, Blueprint, jsonify, request, current_app
import time
from flask_sse import sse
from flask_socketio import SocketIO, emit, disconnect
from flask_mail import Mail, Message
import secrets
import string
from werkzeug.security import check_password_hash, generate_password_hash
import pysam
from werkzeug.middleware.proxy_fix import ProxyFix



# Define where files will be uploaded
UPLOAD_FOLDER = 'data'

website_name = os.environ.get("WEBSITE_NAME", "default_website_name")
redis_port = os.environ.get("REDIS_PORT", "6379")
app = Flask(__name__)
CORS(app, supports_credentials=True, origins="*")  # Enable CORS to avoid issues when calling from a different frontend
#blueprint = Blueprint("foo", __name__, url_prefix="/api/bar")
#CORS(blueprint)
#with app.app_context():
#    app.register_blueprint(sse, url_prefix='/stream')
app.secret_key = '2eb189a5bf52a9bd074be4f5e0a3a14adcdab32ae318f5ef77bfe99322926fc8'
app.config.from_object("project.config.Config")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # Set a 50 MB limit (for example)
app.config['WTF_CSRF_ENABLED'] = True
app.config['REDIS_URL'] = f"redis://redis:{redis_port}/0"
app.config['QUEUES'] = ["default"]
app.config['SESSION_COOKIE_SAMESITE'] = "Strict"  # Or 'None' for cross-origin requests
app.config['SESSION_COOKIE_SECURE'] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Change as needed
app.config['MAIL_PORT'] = 465  # Or 587 for TLS
app.config['MAIL_USERNAME'] = 'sorteo.los.castro@gmail.com'  # Your email
app.config['MAIL_PASSWORD'] = 'mibicjwcdluscpku'  # Your email password
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEFAULT_SENDER'] = 'sorteo.los.castro@gmail.com'

mail = Mail(app)
db = SQLAlchemy(app)
r = redis.from_url(app.config["REDIS_URL"])

# Initialize Flask-SocketIO with Redis message queue
socketio = SocketIO(app, message_queue=app.config["REDIS_URL"], cors_allowed_origins="*")

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
        
# Dictionary to store connected clients and their roles
connected_clients = {}

@app.route("/api/notifications", methods=["GET"])
@login_required
def get_notifications():
    # Query both dismissed and undismissed notifications for the user
    notifications = Notification.query.filter_by(user_email=current_user.id).all()

    # Separate dismissed and undismissed notifications
    dismissed_notifications = [n.to_dict() for n in notifications if n.is_dismissed]
    undismissed_notifications = [n.to_dict() for n in notifications if not n.is_dismissed]

    return jsonify({
        "undismissed": undismissed_notifications,
        "dismissed": dismissed_notifications
    }), 200

# Emit messages to all clients when a message is published to Redis
def save_notification(email, message):
    with app.app_context():
        notification = Notification(user_email=email, message=message, is_dismissed=False)
        db.session.add(notification)
        db.session.commit()
        return notification.id


def publish_message_to_clients(channel, data):
    for sid, client_info in connected_clients.items():
        role = client_info.get("role")
        email = client_info.get("email")
        
        # Determine message based on role
        if role == "superuser" and ']' in data:
            message = f"[SUPERUSER] {data.split(']')[1]}"
        elif role == "user":
            if data.startswith("[UPLOAD]"):
                message = f"A new upload of sample {data.split('s upload of sample')[1]}"
            elif data.startswith("[ANALYSIS COMPLETE]"):
                message = f"A new analysis of sample {data.split('s analysis of sample')[1]}"
            elif data.startswith("[NEW ORG]"):
                message = "A new participant has been registered."
            else:
                message = f"[USER] {data}"
        else:
            message = f"[UNKNOWN ROLE] {data}"

        # Save notification to the database and get the notification id
        notification_id = save_notification(email, message)  # Assuming this function returns the id of the saved notification

        # Emit message to connected clients with the notification id
        socketio.emit("my response", {"channel": channel, "message": message, "id": notification_id, "created_at":str(datetime.now())}, room=sid)
        print(f"Emitting message for {email} with role {role} and notification id {notification_id}")

# Background task to listen to Redis
def redis_listener():
    pubsub = r.pubsub()
    pubsub.subscribe("chat")
    for message in pubsub.listen():
        if message["type"] == "message":
            data = message["data"]
            if isinstance(data, bytes):
                message_text = data.decode()
                publish_message_to_clients("chat", message_text)

@socketio.on("connect")
def handle_connect():
    query_params = request.args
    role = query_params.get("role", "user")
    email = query_params.get("email", "unknown")

    connected_clients[request.sid] = {"role": role, "email": email}
    print(f"User connected: {email}, Role: {role}")

    # Fetch undismissed notifications from the database
    undismissed_notifications = Notification.query.filter_by(user_email=email, is_dismissed=False).all()
    notifications = [n.to_dict() for n in undismissed_notifications]

    # Send undismissed notifications to the client
    emit("my response", {"data": f"Connected as {role}"})
    emit("notifications", {"undismissed": notifications})

@app.route("/api/notifications/dismiss", methods=["POST"])
@login_required
def dismiss_notification():
    if request.method == 'OPTIONS' or request.method == 'GET':
        return '', 204
    data = request.form
    notification_id = data.get("id")

    # Update notification status in the database
    notification = Notification.query.filter_by(id=notification_id, user_email=current_user.id).first()
    if notification:
        notification.is_dismissed = True
        db.session.commit()
        return {"success": True}, 200
    return {"error": "Notification not found"}, 404

# Start the Redis listener as a background task
@socketio.on('start_redis_listener')
def start_listener():
    if not hasattr(start_listener, 'started'):
        # If listener hasn't started yet, start it
        socketio.start_background_task(target=redis_listener)
        start_listener.started = True  # Mark listener as started
    else:
        print("Redis listener is already running.")

@socketio.on("disconnect")
def handle_disconnect():
    client_info = connected_clients.pop(request.sid, None)
    if client_info:
        print(f"User disconnected: {client_info.get('email')}, Role: {client_info.get('role')}")

@socketio.on('my event')
def test_message(message):
    print(f"Received message: {message}")
    emit('my response', {'data': message['data']})

@socketio.on('my broadcast event')
def test_broadcast_message(message):
    print(f"Broadcasting message: {message}")
    emit('my response', {'data': message['data']}, broadcast=True)

@app.route('/hello')
def publish_hello():
    r.publish("chat", "Hello!")
    print("hi")
    #sse.publish({"message": "Hello!"}, type='notification')
    return jsonify({"message": "Hello!"}), 200

@app.route('/pub')
def publish_pub():
    r.publish("chat", "Pub!")
    #sse.publish({"message": "Pub 2!"}, type='notification')
    return jsonify({"message": "Pub 2!"}), 200

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# flask-login users  
class flaskLoginUser(UserMixin):
    def __init__(self, email, organization, role="user"):
        self.id = email
        self.role = role
        self.organization = organization
        
    def __repr__(self):
        return "%s" % ( self.id)
    def is_active(self):
        return True

    def is_superuser(self):
        return self.role == "superuser"

#Login form
class LoginForm(Form):
    username = StringField('Your username', validators=[DataRequired()])
    password = PasswordField('Your password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

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

# User loader function
@login_manager.user_loader
def load_user(user_id):
    print(user_id)
    user = User.query.filter_by(email=user_id).first() 
    if user:
        return flaskLoginUser(user.email,role=user.role, organization=user.organization.name)  # Or return a custom user object if needed
    return None

def create_task(task_type):
    time.sleep(int(task_type) * 10)
    return True
@app.route("/api/tasks", methods=["POST"])
def run_task():
    task_type = request.form["type"]
    with Connection(redis.from_url(app.config["REDIS_URL"])):
        q = Queue()
        task = q.enqueue(create_task, task_type)
    response_object = {
        "status": "success",
        "data": {
            "task_id": task.get_id()
        }
    }
    return jsonify(response_object), 202
@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_status(task_id):
    with Connection(redis.from_url(current_app.config["REDIS_URL"])):
        q = Queue()
        task = q.fetch_job(task_id)
    if task:
        response_object = {
            "status": "success",
            "data": {
                "task_id": task.get_id(),
                "task_status": task.get_status(),
                "task_result": task.result,
            },
        }
    else:
        response_object = {"status": "error"}
    return jsonify(response_object)

# This one is for general use (works with all HTTP methods)
def role_required(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                abort(403)  # Forbidden
            return func(*args, **kwargs)
        return wrapper
    return decorator

# This one is for POST requests only
def role_required_for_post(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.method == 'POST':
                if not current_user.is_authenticated or current_user.role != role:
                    abort(403)  # Forbidden
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Login route
@app.route("/api/login", methods=["POST", "GET"])
def login():
    if request.method == 'OPTIONS':
        return '', 204
    username = request.form.get("username")#several users of same name?
    password = request.form.get("password")
    print(f"Attempted login with username: {username}")

    # Query the User model to find the user by their 'username' (or 'email')
    user = User.query.filter_by(username=username).first()  # Or filter by 'username' if that's what you use
    print(user)
    if user and check_password_hash(user.password, password):  # Check if passwords match
        # Use Flask-Login's login_user to log the user in
        login_user(flaskLoginUser(user.email,role=user.role, organization=user.organization.name))

        # Return a successful response with user role and other information
        return jsonify({"message": "Login successful", "role": user.role, "email": user.email}), 200

    # If the user is not found or the password is incorrect
    return jsonify({"error": "Invalid username or password"}), 401

# Logout route
@app.route("/api/logout", methods=["POST"])
def logout():
    print(f"Current user authenticated: {current_user.is_authenticated}")  # Debugging
    print(f"Current user: {current_user}")
    if current_user.is_authenticated:
        logout_user()
        return jsonify({"message": "Logged out successfully"}), 200
    return jsonify({"error": "No user is logged in"}), 400
    
@app.route("/api/user", methods=["GET"])
@login_required
def get_user_info():
    return jsonify({
        "username": current_user.id,
        "organization": current_user.organization,
        "email": current_user.id,
        "role": current_user.role
    }), 200


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

@app.route('/api/distributions_participants', methods=['GET'])
@login_required
@role_required("superuser")
def get_all():
    # Retrieve all distributions and organizations from the database
    distributions = Distribution.query.all()
    organizations = Organization.query.all()

    # Serialize distributions, including their associated organizations
    distribution_list = []
    for dist in distributions:
        distribution_list.append({
            "id": dist.id,
            "name": dist.name,
            "samples": dist.samples,
            "organizations": [
                {"id": org.id, "name": org.name} for org in dist.organizations
            ]
        })

    # Serialize organizations, including their associated distributions
    organization_list = []
    for org in organizations:
        organization_list.append(org.name)

    # Return the data as JSON
    return jsonify({
        "distributions": distribution_list,
        "organizations": organization_list
    })

@app.route('/api/assign_participant', methods=['POST'])
@login_required
@role_required_for_post("superuser")
def assign_participant():
    data = request.get_json()
    print(data)

    participant_name = data.get("participant")
    distribution_name = data.get("distribution")

    if not participant_name or not distribution_name:
        return jsonify({"error": "Missing participant or distribution name"}), 400

    # Fetch participant and distribution by name
    participant = Organization.query.filter_by(name=participant_name).first()
    distribution = Distribution.query.filter_by(name=distribution_name).first()

    if not participant or not distribution:
        return jsonify({"error": "Invalid participant or distribution name"}), 404

    # Check if the participant is already assigned
    if participant in distribution.organizations:
        return jsonify({"message": "Participant already assigned"}), 200

    # Assign the participant to the distribution
    distribution.organizations.append(participant)
    db.session.commit()

    return jsonify({"message": f"Participant {participant.name} assigned to {distribution.name}"}), 200


    
@app.route("/api/distribution_data/<distribution>", methods=["GET"])
@login_required
def get_distribution_data(distribution):
    print("Sample data request received")  # Debugging line
    dist = Distribution.query.filter_by(name=distribution).first()
    base_dir = f"data/{dist.name}"  # Root directory for lab reports
    import subprocess
    subprocess.call("ls data", shell=True)
    
    # Load sample-reference mapping from samples.txt
    samples_file = f"{base_dir}/samples.txt"
    sample_reference_map = {}
    try:
        with open(samples_file, "r") as f:
            for line in f:
                sample_id, reference = line.strip().split()
                sample_reference_map[sample_id] = reference
    except FileNotFoundError:
        print(f"File not found: {samples_file}")
        return jsonify({"error": "Samples file not found"}), 404
    except Exception as e:
        print(f"Error reading samples.txt: {e}")
        return jsonify({"error": "Failed to process samples file"}), 500

    # Process reports and aggregate distribution data
    report_data = process_all_reports(base_dir)
    distribution_data = {}  # {sample_name: {"participants": int, "metrics": dict, "reference": str}}
    for lab, samples in report_data.items():
        for sample_name, metrics in samples.items():
            if sample_name not in distribution_data:
                distribution_data[sample_name] = {
                    "participants": 0,
                    "reference": sample_reference_map.get(sample_name, "Unknown")  # Add reference info
                }
            distribution_data[sample_name]["participants"] += 1

    return jsonify(distribution_data)

@app.route("/api/proxy_fasta_EPI_ISL_412866")
#@login_required
def proxy_fasta1():
    return app.send_static_file('genomes/EPI_ISL_412866/EPI_ISL_412866.fasta')
    
@app.route("/api/proxy_fai_EPI_ISL_412866")
#@login_required
def proxy_fai1():
    return app.send_static_file('genomes/EPI_ISL_412866/EPI_ISL_412866.fasta.fai')

@app.route("/api/proxy_gzi_EPI_ISL_412866")
#@login_required
def proxy_gzi1():
    return app.send_static_file('genomes/EPI_ISL_412866/EPI_ISL_412866.fasta.gz')

@app.route("/api/proxy_gff3_EPI_ISL_412866")
#@login_required
def proxy_gff1():
    return app.send_static_file('genomes/EPI_ISL_412866/EPI_ISL_412866.gff3')

@app.route("/api/proxy_fasta_EPI_ISL_1653999")
#@login_required
def proxy_fasta2():
    return app.send_static_file('genomes/EPI_ISL_1653999/EPI_ISL_1653999.fasta')
    
@app.route("/api/proxy_fai_EPI_ISL_1653999")
#@login_required
def proxy_fai2():
    return app.send_static_file('genomes/EPI_ISL_1653999/EPI_ISL_1653999.fasta.fai')

@app.route("/api/proxy_gzi_EPI_ISL_1653999")
#@login_required
def proxy_gzi2():
    return app.send_static_file('genomes/EPI_ISL_1653999/EPI_ISL_1653999.fasta.gz')

@app.route("/api/proxy_gff3_EPI_ISL_1653999")
#@login_required
def proxy_gff2():
    return app.send_static_file('genomes/EPI_ISL_1653999/EPI_ISL_1653999.gff3')

# Route to serve static bam
@app.route("/api/distribution_data/<distribution>/sample/<selected_sample>/participant/<participant>", methods=["GET"])
#@login_required
def get_sample_bam(distribution,selected_sample,participant):
    print(f"Request received for bams")  # Debugging line
    # Define the directory where your files are stored
    dist = Distribution.query.filter_by(name=distribution).first()
    file_path = f"/usr/src/app/data/{dist.name}/{participant}/{selected_sample}/{participant}_{selected_sample}_consensus.bam"  # Replace with your directory
    print(file_path)

    # Check if the file exists
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    # Serve the file
    try:
        return send_file(file_path, as_attachment=True, mimetype='application/octet-stream')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to serve static bais ################################ BEWARE NO VALIDATION TO DOWNLOAD BAM FILES FOR JBROWSE, SO ANYONE CAN ACCESS, just add user and password and validate here
@app.route("/api/distribution_data/<distribution>/sample/<selected_sample>/participant/<participant>.bai", methods=["GET"])
#@login_required
def get_sample_bai(distribution,selected_sample,participant):
    print(f"Request received for bais")  # Debugging line
    # Define the directory where your files are stored
    dist = Distribution.query.filter_by(name=distribution).first()
    file_path = f"/usr/src/app/data/{dist.name}/{participant}/{selected_sample}/{participant}_{selected_sample}_consensus.bam.bai"  # Replace with your directory
    print(file_path)

    # Check if the file exists
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    # Serve the file
    try:
        return send_file(file_path, as_attachment=True, mimetype='application/octet-stream')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to serve static bigwig
@app.route("/api/distribution_data/<distribution>/sample/<selected_sample>/participant/<participant>.bw", methods=["GET"])
#@login_required
def get_sample_bigwig(distribution,selected_sample,participant):
    print(f"Request received for bams")  # Debugging line
    # Define the directory where your files are stored
    dist = Distribution.query.filter_by(name=distribution).first()
    file_path = f"/usr/src/app/data/{dist.name}/{participant}/{selected_sample}/{participant}_{selected_sample}.bw"  # Replace with your directory
    print(file_path)

    # Check if the file exists
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    # Serve the file
    try:
        return send_file(file_path, as_attachment=True, mimetype='application/octet-stream')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/distribution_data/<distribution>/sample/<selected_sample>", methods=["GET"])
@login_required
def get_sample_details(distribution, selected_sample):
    print(f"Request received for sample: {selected_sample}")  # Debugging line
    print(distribution)
    dist = Distribution.query.filter_by(name=distribution).first()
    base_dir = f"data/{dist.name}"  # Root directory for lab reports
    print(base_dir)
    report_data = process_all_reports(base_dir)

    sample_details = {}  # {sample_name: {"participants": int, "metrics": dict}}
    for lab, samples in report_data.items():
        for sample_name, metrics in samples.items():
            if sample_name not in sample_details:
                sample_details[sample_name] = {
                    "participants": 0,
                    "metrics": {},
                }
            sample_details[sample_name]["metrics"][lab] = metrics
            sample_details[sample_name]["participants"] += 1

    # Handle form submission
    if selected_sample in sample_details:
        # Prepare table data and FASTA URLs
        table_data = []
        bams = []
        bigwigs = []
        for lab, metrics in sample_details[selected_sample]["metrics"].items():
            if metrics["coverage"] == "N/A":
                table_data.append({
                "participant": lab,
                "coverage": 'N/A',
                "ns": 'N/A',
                "similarity": 'N/A',
                "read_coverage": 'N/A',
                "clade":'N/A',
                "G_clade":'N/A'
                })
                continue  # Skip this lab if coverage is not a number

            read_coverage=round(metrics["Mean coverage depth"], 2) if metrics["Mean coverage depth"]!="N/A" else "N/A"
            table_data.append({
                "participant": lab,
                "coverage": round(metrics["coverage"] * 100, 2),
                "ns": round(metrics["Ns"], 2),
                "similarity": round(metrics["similarity"], 2),
                "read_coverage": read_coverage,
                "clade":metrics["clade"],
                "G_clade":metrics["G_clade"]
            })
            if read_coverage!="N/A":
                bam_url = f"http://{website_name}/api/distribution_data/{distribution}/sample/{selected_sample}/participant/{lab}"
                bigwig_url = f"http://{website_name}/api/distribution_data/{distribution}/sample/{selected_sample}/participant/{lab}.bw"
                bams.append(bam_url)
                bigwigs.append(bigwig_url)
        if current_user.is_superuser():
            return jsonify({"table": table_data, "bams": bams, "bigwigs": bigwigs})
        else:
            print('non superuser')
            user_lab = current_user.organization
            if user_lab not in sample_details[selected_sample]["metrics"]:
                return jsonify({"error": "You have not submitted valid data for this sample."}), 404

            # Filter user lab data
            user_metrics = sample_details[selected_sample]["metrics"][user_lab]
            if user_metrics["coverage"]=="N/A":
                return jsonify({"error": "You have not submitted valid data for this sample."}), 404
            print(user_metrics)
            user_bam_url=[]
            user_bigwig_url=[]
            plot_url=""
            if "Mean coverage depth" in user_metrics and user_metrics["Mean coverage depth"]!="N/A":
                user_bam_url = [f"http://{website_name}/api/distribution_data/{distribution}/sample/{selected_sample}/participant/{user_lab}"]
                user_bigwig_url = [f"http://{website_name}/api/distribution_data/{distribution}/sample/{selected_sample}/participant/{user_lab}.bw"]

            # Aggregate metrics from other labs
            aggregated_metrics = {
                "coverage": 0,
                "ns": 0,
                "similarity": 0,
                "read_coverage": 0,
                "lab_count": 0,
                "clade":"",
                "G_clade":""
            }

            clade_counts = {}
            g_clade_counts = {}

            for lab, metrics in sample_details[selected_sample]["metrics"].items():
                if lab != user_lab and lab != "9999":  # Aggregate metrics from other labs
                    if metrics["coverage"] == "N/A":
                        continue  # Skip this lab if coverage is not a number
                    aggregated_metrics["coverage"] += metrics["coverage"]
                    aggregated_metrics["ns"] += metrics["Ns"]
                    aggregated_metrics["similarity"] += metrics["similarity"]
                    if metrics["Mean coverage depth"]!="N/A":
                        aggregated_metrics["read_coverage"] += metrics["Mean coverage depth"]
                    aggregated_metrics["lab_count"] += 1

                    # Count clade occurrences
                    clade = metrics.get("clade", "")
                    g_clade = metrics.get("G_clade", "")
                    if clade:
                        clade_counts[clade] = clade_counts.get(clade, 0) + 1
                    if g_clade:
                        g_clade_counts[g_clade] = g_clade_counts.get(g_clade, 0) + 1

            # Calculate averages for aggregated metrics
            if aggregated_metrics["lab_count"] > 0:
                aggregated_metrics["coverage"] = round(
                    (aggregated_metrics["coverage"] / aggregated_metrics["lab_count"]) * 100, 2
                )
                aggregated_metrics["ns"] = round(
                    aggregated_metrics["ns"] / aggregated_metrics["lab_count"], 2
                )
                aggregated_metrics["similarity"] = round(
                    aggregated_metrics["similarity"] / aggregated_metrics["lab_count"], 2
                )
                aggregated_metrics["read_coverage"] = round(
                    aggregated_metrics["read_coverage"] / aggregated_metrics["lab_count"], 2
                )

            # Determine the most frequent clade and G_clade
            if clade_counts:
                aggregated_metrics["clade"] = max(clade_counts, key=clade_counts.get)
            if g_clade_counts:
                aggregated_metrics["G_clade"] = max(g_clade_counts, key=g_clade_counts.get)

            # Extract reference lab metrics (Lab 9999)
            ref_lab = "9999"
            ref_metrics = sample_details[selected_sample]["metrics"].get(ref_lab, None)
            if not ref_metrics:
                return jsonify({"error": "Reference lab data not found"}), 404
            
            # Prepare response table data
            others_label="Others ("+str(aggregated_metrics["lab_count"])+")"
            user_table_data = [
                {
                    "participant": user_lab,
                    "coverage": round(user_metrics["coverage"] * 100, 2),
                    "ns": round(user_metrics["Ns"], 2),
                    "similarity": round(user_metrics["similarity"], 2),
                    "read_coverage": round(user_metrics["Mean coverage depth"], 2),
                    "clade":user_metrics["clade"],
                    "G_clade":user_metrics["G_clade"]
                },
                {
                    "participant": others_label,
                    "coverage": aggregated_metrics["coverage"],
                    "ns": aggregated_metrics["ns"],
                    "similarity": aggregated_metrics["similarity"],
                    "read_coverage": aggregated_metrics["read_coverage"],
                    "clade":aggregated_metrics["clade"],
                    "G_clade":aggregated_metrics["G_clade"]
                },
                {
                    "participant": "Reference",
                    "coverage": round(ref_metrics["coverage"] * 100, 2),
                    "ns": round(ref_metrics["Ns"], 2),
                    "similarity": round(ref_metrics["similarity"], 2),
                    "read_coverage": round(ref_metrics["Mean coverage depth"], 2),
                    "clade":ref_metrics["clade"],
                    "G_clade":ref_metrics["G_clade"]
                }
            ]

            return jsonify({"table": user_table_data, "bams": user_bam_url, "bigwigs": user_bigwig_url})

    return jsonify({"error": "Sample not found"}), 404

@app.route("/api/create_distributions", methods=["GET", "POST"], strict_slashes=False)
@login_required
@role_required_for_post("superuser")
def distribution_manager():
    if request.method == "GET":
        # Fetch all distributions from the database
        distributions = Distribution.query.all()
        return jsonify({
            "distributions": [d.name for d in distributions]
        }), 200

    if request.method == "POST":
        distribution_name = request.form.get('name')

        if not distribution_name:
            return jsonify({"error": "Distribution name is required"}), 400

        # Check if distribution already exists
        if Distribution.query.filter_by(name=distribution_name).first():
            return jsonify({"error": "Distribution already exists"}), 400

        # Create a new distribution
        new_distribution = Distribution(
            name=distribution_name,
            samples=[]  # Directly pass list; SQLAlchemy handles JSON serialization
        )
        db.session.add(new_distribution)
        db.session.commit()

        os.makedirs(f"data/{distribution_name}")

        return jsonify({"message": f"Distribution '{distribution_name}' created successfully"}), 201

@app.route("/api/create_or_restore_organization", methods=["POST"], strict_slashes=False)
@login_required
@role_required_for_post("superuser")
def create_or_restore_organization_with_user():
    # Get data from the request
    organization_name = request.form.get('name')
    organization_email = request.form.get('email')
    organization_username = request.form.get('username')
    is_restore = request.form.get('restore', 'false').lower() == 'true'  # Default to "create"

    # Validate required fields
    if not organization_name or not organization_email or not organization_username:
        return jsonify({"error": "Organization name, email, and username are required"}), 400

    # Handle Restore Password
    if is_restore:
        # Look up the user by email and username
        user = User.query.filter_by(email=organization_email, username=organization_username).first()

        if not user:
            return jsonify({"error": "No user found with the provided email and username"}), 404

        # Generate a random password
        def generate_random_password(length=12):
            characters = string.ascii_letters + string.digits + string.punctuation
            return ''.join(secrets.choice(characters) for i in range(length))

        random_password = generate_random_password()

        # Update the user's password
        user.password = generate_password_hash(random_password)
        db.session.commit()

        # Send password reset email
        try:
            msg = Message(
                'Password Reset Request',
                recipients=[organization_email]
            )
            msg.body = f"""\ 
            Hello {organization_username},

            Your password has been successfully reset for the RSV EQA dashboard site, representing {organization_name}.

            Your new login credentials are:
            - Username: {organization_username}
            - Password: {random_password}

            Please log in and change your password as soon as possible using the link below:
            http://{website_name}/change-password/

            Best regards,
            The RSV EQA Team
            """
            mail.send(msg)

        except Exception as e:
            print("Failed to send email:", e)
            return jsonify({"error": "Password reset, but email could not be sent."}), 500

        return jsonify({
            "message": f"Password reset for user '{organization_username}' successfully. A reset email has been sent."
        }), 200

    # Handle Create Organization
    # Check if the organization already exists
    if Organization.query.filter_by(name=organization_name).first():
        return jsonify({"error": "Organization already exists"}), 400

    # Check if the username or email is already taken
    if User.query.filter(User.email == organization_email).first():
        return jsonify({"error": "Email is already in use"}), 400

    # Create the organization
    new_organization = Organization(name=organization_name)
    db.session.add(new_organization)
    db.session.flush()  # Get the ID of the newly created organization

    # Generate a random password
    def generate_random_password(length=12):
        characters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(characters) for i in range(length))

    random_password = generate_random_password()

    # Create the user and associate it with the organization
    new_user = User(
        email=organization_email,
        username=organization_username,
        password=generate_password_hash(random_password),  # Save the random password
        role="user",
        organization=new_organization
    )
    db.session.add(new_user)
    db.session.commit()
    r.publish("chat", f"[NEW ORG]New participant {organization_name} has joined.")

    # Send welcome email
    try:
        msg = Message(
            'Welcome to RSV EQA!',
            recipients=[organization_email]
        )
        msg.body = f"""\ 
        Hello {organization_username},

        Welcome to RSV EQA dashboard site, representing {organization_name}!

        Your account has been created with the following details:
        - Username: {organization_username}
        - Password: {random_password}

        If you would like to change your password, please visit the link below:
        http://{website_name}/change-password

        Best regards,
        The RSV EQA Team
        """
        mail.send(msg)

    except Exception as e:
        print("Failed to send email:", e)
        return jsonify({"error": "Organization created, but email could not be sent."}), 500

    return jsonify({
        "message": f"Organization '{organization_name}' and user '{organization_username}' created successfully. A welcome email has been sent."
    }), 201


@app.route('/verify_old_password', methods=['POST'])
@login_required
def verify_old_password():
    old_password = request.form.get("oldPassword")
    email = current_user.id

    # Get the current user's password hash
    user = User.query.filter_by(email=email).first() 
    print(user)

    # Check if the old password matches the stored hash
    if not check_password_hash(user.password, old_password):
        return jsonify({"error": "Old password is incorrect"}), 400

    return jsonify({"message": "Old password is correct"}), 200

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    new_password = request.form.get("newPassword")
    email = current_user.id

    # Hash the new password before storing it
    user = User.query.filter_by(email=email).first() 
    user.password = generate_password_hash(new_password)

    db.session.commit()

    return jsonify({"message": "Password changed successfully!"}), 200
    
@app.route("/api/distributions/<distribution>/samples", methods=["GET", "POST"], strict_slashes=False)
@login_required
@role_required_for_post("superuser")
def samples_per_distro_manager(distribution):
    if request.method == "GET":
        # Fetch the distribution from the database
        distribution_record = Distribution.query.filter_by(name=distribution).first()

        if not distribution_record:
            return jsonify({"error": f"Distribution '{distribution}' not found"}), 404

        # Return the list of samples
        samples = distribution_record.samples or []
        print(samples)
        return jsonify({"distribution": distribution, "samples": samples}), 200

    elif request.method == "POST":
        sample_name = request.form.get("sample")
        rsv_type = 'EPI_ISL_1653999' if request.form.get("rsv_type")=='RSV-B' else 'EPI_ISL_412866'  # Get RSV type

        if not sample_name:
            return jsonify({"error": "Sample name is required"}), 400

        # Fetch the distribution from the database
        distribution_record = Distribution.query.filter_by(name=distribution).first()
        
        if not distribution_record:
            return jsonify({"error": f"Distribution '{distribution}' not found"}), 404
        
        print(distribution_record.samples)

        # Add the sample to the distribution's samples list
        if distribution_record.samples is None:
            distribution_record.samples = []

        if sample_name in distribution_record.samples:
            return jsonify({"error": f"Sample '{sample_name}' already exists in distribution '{distribution}'"}), 400

        # Append the sample
        distribution_record.samples.append(sample_name)

        # Mark the JSON field as modified
        flag_modified(distribution_record, "samples")

        # Persist the changes
        db.session.add(distribution_record)
        db.session.commit()

         # --- FILE HANDLING SECTION ---
        try:
            # Ensure the folder exists
            os.makedirs(f"data/{distribution}", exist_ok=True)

            # Define the path for samples.txt
            file_path = os.path.join(f"data/{distribution}", "samples.txt")

            # Open file in append mode and write new entry
            with open(file_path, "a") as file:
                file.write(f"{sample_name}\t{rsv_type}\n")

        except Exception as e:
            return jsonify({"error": f"Failed to write to file: {str(e)}"}), 500

        return jsonify({
            "message": f"Sample '{sample_name}' with RSV type '{rsv_type}' added to '{distribution}' and saved in samples.txt"
        }), 201


# Upload route
@app.route("/api/upload", methods=["POST"])
@login_required  # Ensure the user is authenticated
def upload_files():
    #######################this needs a lot of validation logic, and tasks sendings
    def is_gzip_file(file_path):
        """Check if a file is gzip-compressed."""
        try:
            with gzip.open(file_path, 'rb') as test_gzip:
                test_gzip.read(1)
            return True
        except gzip.BadGzipFile:
            return False
        
    def read_first_lines(file_path, num_lines=4):
        """Read first lines of a file, handling gzip if necessary."""
        open_func = gzip.open if is_gzip_file(file_path) else open
        with open_func(file_path, 'rt') as f:  # Read as text
            return [f.readline().strip() for _ in range(num_lines)]
        
    def is_valid_fasta(file_path):
        """Check if the file is a valid FASTA."""
        try:
            first_line = read_first_lines(file_path, 1)[0]
            return first_line.startswith(">")
        except Exception:
            return False

    def is_valid_bam(file_path):
        """Check if the file is a valid BAM using pysam."""
        try:
            with pysam.AlignmentFile(file_path, "rb") as _:
                return True
        except Exception:
            return False

    def is_valid_fastq(file_path):
        """Check if the file follows the FASTQ format."""
        try:
            lines = read_first_lines(file_path, 4)
            return (lines[0].startswith("@") and
                    all(c in "ATCGN" for c in lines[1]) and
                    lines[2] == "+" and
                    len(lines[1]) == len(lines[3]))
        except Exception:
            return False
    
    # Validate request form data
    required_fields = ['sample', 'distribution', 'organization']
    for field in required_fields:
        if field not in request.form:
            return jsonify({"error": f"{field} is required"}), 400
    
    # Get form data
    fasta_file = request.files.get('fasta')
    bam_file = request.files.get('bam')
    fq1 = request.files.get('fq1')
    fq2 = request.files.get('fq2')
    description = request.form.get('description', '')  # Optional description
    sample = request.form['sample']
    distribution = request.form['distribution']
    organization = request.form['organization']
    
    # Ensure at least one file is provided
    if not any([fasta_file, bam_file, fq1, fq2]):
        return jsonify({"error": "At least one file (fasta, bam or fastq) is required"}), 400

    # Create upload folder
    specific_upload_folder = os.path.join(
        app.config["UPLOAD_FOLDER"], distribution, organization, sample
    )

    samples_txt=os.path.join(
        app.config["UPLOAD_FOLDER"], distribution,"samples.txt")

    # Check if the folder exists, and delete it if it does
    if os.path.exists(specific_upload_folder):
        shutil.rmtree(specific_upload_folder)

    # Now recreate the folder
    os.makedirs(specific_upload_folder, exist_ok=True)

        # Save files with validation
    uploaded_files = {}
    if fasta_file:
        fasta_filename = secure_filename(organization+"_"+sample + "_original.fasta")
        fasta_path = os.path.join(specific_upload_folder, fasta_filename)
        fasta_file.seek(0)
        fasta_file.save(fasta_path)

        if not is_valid_fasta(fasta_path):
            os.remove(fasta_path)
            return jsonify({"error": "Invalid FASTA file"}), 400
        
        uploaded_files['fasta'] = fasta_path

    if bam_file:
        bam_filename = secure_filename(organization+"_"+sample + "_original.bam")
        bam_path = os.path.join(specific_upload_folder, bam_filename)
        bam_file.seek(0)
        bam_file.save(bam_path)

        if not is_valid_bam(bam_path):
            os.remove(bam_path)
            return jsonify({"error": "Invalid BAM file"}), 400
        
        uploaded_files['bam'] = bam_path


    if fq1:
        fq1_is_gzipped = is_gzip_file(fq1)
        fq1_extension = "_original_R1.fastq.gz" if fq1_is_gzipped else "_original_R1.fastq"
        fq1_filename = secure_filename(organization + "_" + sample  + fq1_extension)
        fq1_path = os.path.join(specific_upload_folder, fq1_filename)
        fq1.seek(0)
        fq1.save(fq1_path)

        if not is_valid_fastq(fq1_path):
            os.remove(fq1_path)
            return jsonify({"error": "Invalid FASTQ R1 file"}), 400

        uploaded_files['fq1'] = fq1_path

    if fq2:
        fq2_is_gzipped = is_gzip_file(fq2)
        fq2_extension = "_original_R2.fastq.gz" if fq2_is_gzipped else "_original_R2.fastq"
        fq2_filename = secure_filename(organization + "_" + sample  + fq2_extension)
        fq2_path = os.path.join(specific_upload_folder, fq2_filename)
        fq2.seek(0)
        fq2.save(fq2_path)

        if not is_valid_fastq(fq2_path):
            os.remove(fq2_path)
            return jsonify({"error": "Invalid FASTQ R2 file"}), 400
        
        uploaded_files['fq2'] = fq2_path

    # Copy genomeLength.txt to the specific_upload_folder
    genome_length_file = os.path.join(app.config["UPLOAD_FOLDER"], "genomeLength.txt")
    genome_length_dest = os.path.join(specific_upload_folder, "genomeLength.txt")
    if os.path.exists(genome_length_file):
        shutil.copy(genome_length_file, genome_length_dest)
        uploaded_files['genomeLength'] = genome_length_dest
    else:
        return jsonify({"error": "genomeLength.txt not found in the upload folder"}), 400

    # Enqueue task to process files and launch workflow asynchronously
    with Connection(redis.from_url(app.config["REDIS_URL"])):
        q = Queue()
        task = q.enqueue(launch_nextflow, specific_upload_folder, "main.nf", {"reads": specific_upload_folder+"", "samples_txt": samples_txt})

    r.publish("chat",f"[UPLOAD]{organization}'s upload of sample {sample} from distribution {distribution} has been completed.")

    # Return response with task information
    return jsonify({
        "message": "Files uploaded successfully, task queued.",
        "uploaded_files": uploaded_files,
        "task_id": task.get_id(),
    }), 201


'''def process_uploaded_files(uploaded_files, sample, description):
    """
    Background task to process uploaded files.
    """
    print(f"Processing files for sample {sample}: {uploaded_files}")
    # Add your processing logic here (e.g., alignments, QC checks, etc.)
    # This is a background task running in the RQ worker
    return f"Processing completed for sample {sample}"'''

# Task function for launching Nextflow
def launch_nextflow(upload_dir, workflow_name="main.nf", params={}):
    """Run the Nextflow workflow."""
    try:
        # Construct the command with escaped spaces
        cmd = " ".join([
            "nextflow", "run", workflow_name, "--reads=" + params['reads'].replace(' ', '\\ ') + "/","--samples_txt=" + params['samples_txt'].replace(' ', '\\ '), "-resume"
        ])

        print(cmd)
        
        # Log the command being executed
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] Command: {cmd}")
        
        # Execute the workflow
        process = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        # Log stdout and stderr
        stdout_timestamp = datetime.now().isoformat()
        print(f"[{stdout_timestamp}] STDOUT:\n{process.stdout}")
        
        stderr_timestamp = datetime.now().isoformat()
        if process.stderr:
            print(f"[{stderr_timestamp}] STDERR:\n{process.stderr}")

        distribution, organization, sample=upload_dir.split("/")[-3],upload_dir.split("/")[-2],upload_dir.split("/")[-1]
        r.publish("chat", f"[ANALYSIS COMPLETE]{organization}'s analysis of sample {sample} from distribution {distribution} has been completed.")
        
        # Return the result
        return {
            "status": "success" if process.returncode == 0 else "failed",
            "stdout": process.stdout,
            "stderr": process.stderr
        }
    except Exception as e:
        error_timestamp = datetime.now().isoformat()
        print(f"[{error_timestamp}] Exception: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


# Test authentication route
@app.route("/api/test", methods=["GET"])
def test_route():
    if not current_user.is_authenticated:
        return jsonify({"message": "User not authenticated"}), 401
    return jsonify({"message": "User is authenticated!"}), 200




##############################


    

@app.route("/api/")
def hello_world():
    return jsonify(hello="world")


@app.route("/api/static/<path:filename>")
def staticfiles(filename):
    return send_from_directory(app.config["STATIC_FOLDER"], filename)


@app.route("/api/media/<path:filename>")
def mediafiles(filename):
    return send_from_directory(app.config["MEDIA_FOLDER"], filename)


@app.route("/api/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file = request.files["file"]
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["MEDIA_FOLDER"], filename))
    return """
    <!doctype html>
    <title>upload new File</title>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file><input type=submit value=Upload>
    </form>
    """

@app.route("/api/download_docx/<distribution>")
@login_required
def download_docx(distribution):
    """Route for generating the DOCX report."""
    dist = Distribution.query.filter_by(name=distribution).first()
    base_dir = f"data/{dist.name}"  # Root directory for lab reports
    report_data = process_all_reports(base_dir)

    # Generate the DOCX file using the refactored function
    doc = generate_docx_report(report_data, base_dir, current_user.role, current_user.organization, distribution)

    # Save the DOCX file to a temporary file
    file_path = "/usr/src/app/project/temp_report.docx"
    doc.save(file_path)

    # Send the file to the user
    return send_file(file_path, as_attachment=True)

