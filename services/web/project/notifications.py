from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required
from project.utils.sql_models import db, User, Distribution, Organization, Notification
import os, redis
from datetime import datetime
from flask_socketio import SocketIO, emit, disconnect

# Create the blueprint
notif_bp = Blueprint('notifications', __name__)
website_name = os.environ.get("WEBSITE_NAME", "default_website_name")
# Dictionary to store connected clients and their roles
connected_clients = {}
# Initialize Flask-SocketIO
socketio = SocketIO(cors_allowed_origins="*")


@notif_bp.route("/api/notifications", methods=["GET"])
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
    with current_app.app_context():
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
def redis_listener(r):
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

@notif_bp.route("/api/notifications/dismiss", methods=["POST"])
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
        redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        socketio.start_background_task(target=redis_listener(r))
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

@notif_bp.route('/hello')
def publish_hello():
    redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(redis_url)
    r.publish("chat", "Hello!")
    print("hi")
    #sse.publish({"message": "Hello!"}, type='notification')
    return jsonify({"message": "Hello!"}), 200

@notif_bp.route('/pub')
def publish_pub():
    redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(redis_url)
    r.publish("chat", "Pub!")
    #sse.publish({"message": "Pub 2!"}, type='notification')
    return jsonify({"message": "Pub 2!"}), 200

