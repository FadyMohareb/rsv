"""
__init__.py
============

This module initialises the app, registers module blueprints and sets app configs, and initiates the redis, login, socket, database and mail listeners and managers.

Functions:
    None

:author: Kevin
:version: 0.0.1
:date: 2025-02-20
"""
# Imports
from flask import Flask, request
from flask_cors import CORS
import os, redis

# Blueprints
from .admin import mail,admin_bp
from .notifications import socketio, notif_bp
from .authentication import login_manager, auth_bp
from .upload import upload_bp
from .data import data_bp

# Database utils
from project.utils.sql_models import db

# Define where files will be uploaded
UPLOAD_FOLDER = 'data'

website_name = os.environ.get("WEBSITE_NAME", "default_website_name")
subdirectory_name = os.environ.get("SUBDIRECTORY_NAME", "default_subdirectory_name")
redis_port = os.environ.get("REDIS_PORT", "6379")

# Initiate app
app = Flask(__name__)
# Register blueprints (containing all the REST endpoints and extra logic) in the app
for bp in [admin_bp,notif_bp,auth_bp,upload_bp, data_bp]:
    app.register_blueprint(bp, url_prefix=f'{subdirectory_name}/')
CORS(app, supports_credentials=True, origins="*")  # Enable CORS to avoid issues when calling from a different frontend
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

mail.init_app(app)
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "authentication.login"
r = redis.from_url(app.config["REDIS_URL"])
socketio.init_app(app, message_queue=app.config["REDIS_URL"], path=f"{subdirectory_name}/socket.io")

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)





"""
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
"""


