"""
notifications.py
================

This module handles notifications via Flask endpoints and WebSocket communications.
These functions are mostly used by the frontend's Toolbar.js component.
It provides endpoints for retrieving and dismissing notifications and sets up a 
Redis-based background listener to publish messages to connected WebSocket clients.
WebSocket events are managed via Flask-SocketIO.

Flask endpoints:

    /api/notifications --> get_notifications()
        Retrieves both dismissed and undismissed notifications for the current user.

    /api/notifications/dismiss --> dismiss_notification()
        Marks a specific notification as dismissed for the current user.

    /hello --> publish_hello()
        Publishes a "Hello!" message to the Redis "chat" channel.

    /pub --> publish_pub()
        Publishes a "Pub!" message to the Redis "chat" channel.

WebSocket events:

    connect --> handle_connect()
        Registers a new WebSocket connection, sends initial notifications, and a confirmation message.

    disconnect --> handle_disconnect()
        Removes a disconnected client from the list of connected clients.

    start_redis_listener --> start_listener()
        Starts a background task to listen to Redis for messages.

    my event --> test_message()
        A test event that echoes a received message back to the client.

    my broadcast event --> test_broadcast_message()
        A test event that broadcasts a received message to all connected clients.

Other functions:

    save_notification(email, message)
        Saves a new notification to the database and returns its ID.

    publish_message_to_clients(channel, data)
        Processes and emits a message to all connected WebSocket clients.

    redis_listener(r)
        Listens to a Redis channel ("chat") for new messages and publishes them via WebSocket.

:author: Kevin
:version: 0.0.1
:date: 2025-02-21
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required
from project.utils.sql_models import db, Notification
import os, redis
from datetime import datetime
from flask_socketio import SocketIO, emit

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
    """
    Retrieve notifications for the current user.

    Queries the database for all notifications associated with the logged-in user,
    then separates them into dismissed and undismissed notifications. Returns the results as JSON.

    :return: A JSON response with keys 'undismissed' and 'dismissed', each containing lists of notifications.
    :rtype: flask.Response
    """
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
    """
    Save a new notification to the database.

    Creates a Notification object with the specified email and message, marks it as not dismissed,
    commits the change, and returns the notification's ID.

    :param email: The email address of the user for whom the notification is saved.
    :type email: str
    :param message: The notification message.
    :type message: str
    :return: The ID of the newly created notification.
    :rtype: int
    """
    with current_app.app_context():
        notification = Notification(user_email=email, message=message, is_dismissed=False)
        db.session.add(notification)
        db.session.commit()
        return notification.id


def publish_message_to_clients(channel, data):
    """
    Publish a processed message to all connected WebSocket clients.

    For each connected client, the function determines an appropriate message based on the client's role
    and the provided raw data, saves the notification in the database, and emits the message (along with its ID
    and timestamp) to that client.

    :param channel: The channel name associated with the message.
    :type channel: str
    :param data: The raw message data received (typically from Redis).
    :type data: str
    """
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
    """
    Listen for messages on the Redis "chat" channel and publish them to connected clients.

    Subscribes to the "chat" channel on the provided Redis connection. For each message received,
    decodes the message (if necessary) and calls publish_message_to_clients() to emit the message.

    :param r: A Redis connection object.
    :type r: redis.Redis
    """
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
    """
    Handle a new WebSocket connection.

    Extracts the client's role and email from query parameters, stores them in the connected_clients dictionary,
    retrieves the user's undismissed notifications from the database, and sends both a connection confirmation and
    the notifications to the client.

    """
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
    """
    Mark a notification as dismissed for the current user.

    Expects a notification ID in the form data. If the notification is found and belongs to the current user,
    marks it as dismissed and commits the change to the database.

    """
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
    """
    Start the background Redis listener task if it is not already running.

    Checks if the listener has been started; if not, retrieves the Redis URL from the app configuration,
    creates a Redis connection, and starts the background task that listens for messages on the "chat" channel.
    """
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
    """
    Handle the disconnection of a WebSocket client.

    Removes the client from the connected_clients dictionary and logs the disconnection.
    """
    client_info = connected_clients.pop(request.sid, None)
    if client_info:
        print(f"User disconnected: {client_info.get('email')}, Role: {client_info.get('role')}")

@socketio.on('my event')
def test_message(message):
    """
    Handle a test event by echoing the received message back to the client.

    Logs the received message and emits it back under the 'my response' event.

    :param message: A dictionary containing the data sent by the client.
    :type message: dict
    """
    print(f"Received message: {message}")
    emit('my response', {'data': message['data']})

@socketio.on('my broadcast event')
def test_broadcast_message(message):
    """
    Handle a broadcast event by emitting the received message to all connected clients.

    Logs the message and broadcasts it under the 'my response' event.

    :param message: A dictionary containing the data sent by the client.
    :type message: dict
    """
    print(f"Broadcasting message: {message}")
    emit('my response', {'data': message['data']}, broadcast=True)

@notif_bp.route('/hello')
def publish_hello():
    """
    Publish a "Hello!" message to the Redis "chat" channel.

    Retrieves the Redis URL from the app configuration, creates a connection,
    publishes a "Hello!" message to the "chat" channel, and returns a JSON response.
    Meant for testing purposes.

    :return: A JSON response confirming that the "Hello!" message was published.
    :rtype: flask.Response
    """
    redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(redis_url)
    r.publish("chat", "Hello!")
    print("hi")
    return jsonify({"message": "Hello!"}), 200

@notif_bp.route('/pub')
def publish_pub():
    """
    Publish a "Pub!" message to the Redis "chat" channel.

    Retrieves the Redis URL from the app configuration, creates a connection,
    publishes a "Pub!" message to the "chat" channel, and returns a JSON response.
    Meant for testing purposes.

    :return: A JSON response confirming that the "Pub!" message was published.
    :rtype: flask.Response
    """
    redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(redis_url)
    r.publish("chat", "Pub!")
    return jsonify({"message": "Pub 2!"}), 200

