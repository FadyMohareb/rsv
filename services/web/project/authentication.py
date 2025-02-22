"""
authentication.py
=================

This module provides the functionalities of the authentication system, and endpoints to login/logout, change passwords and verify user information. flask_login is the choice of package to facilitate this.

Flask endpoints:

    /api/login --> login()
        Receives username and password and logs in the user. Logged-in users can later be accessed using flask_login's 'current_user' proxy. WARNING: beware non-unique usernames (not handled currently).

     /api/logout --> logout()
        Logs out the currently authenticated user.

    /api/user --> get_user_info()
        Returns information about the logged-in user, including username, organization, email, and role.

    /api/verify_old_password --> verify_old_password()
        Verifies the user's old password, used as part of the password change process.

    /api/change_password --> change_password()
        Accepts a new password from the user, updates the user's password in the database, and confirms
        the change.

    /api/test --> test_route()
        A simple test endpoint that returns a message indicating whether the user is authenticated.

Other functions:

    flaskLoginUser (class)
        Custom user class implementing flask_login's UserMixin. It represents a user in the system,
        storing the email, organization, and role.

    load_user(user_id)
        Callback function for flask_login that loads a user from the database given a user identifier.

:author: Kevin
:version: 0.0.1
:date: 2025-02-21
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from project.utils.sql_models import db, User
from werkzeug.security import check_password_hash, generate_password_hash
import os
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user 

# Create the blueprint
auth_bp = Blueprint('authentication', __name__)
website_name = os.environ.get("WEBSITE_NAME", "default_website_name")

# flask-login users  
class flaskLoginUser(UserMixin):
    """
    Custom user class for flask_login.
    
    Represents a user in the authentication system.

    :param email: The user's email, used as a unique identifier.
    :type email: str
    :param organization: The organization the user belongs to.
    :type organization: str
    :param role: The user's role, defaults to "user". Can be 'superuser' for admin privileges.
    :type role: str
    """
    def __init__(self, email, organization, role="user"):
        self.id = email
        self.role = role
        self.organization = organization
        
    def __repr__(self):
        """
        Returns the string representation of the user.
        """
        return "%s" % ( self.id)
    
    def is_active(self):
        """
        Indicates whether the user is active.
        
        :return: Always True for active users.
        :rtype: bool
        """
        return True

    def is_superuser(self):
        """
        Checks if the user has superuser privileges.
        
        :return: True if the user's role is 'superuser', otherwise False.
        :rtype: bool
        """
        return self.role == "superuser"

# Initialize Flask-Login
login_manager = LoginManager()

# User loader function
@login_manager.user_loader
def load_user(user_id):
    """
    Load a user from the database given a user identifier.

    :param user_id: The unique identifier of the user (email).
    :type user_id: str
    :return: An instance of flaskLoginUser if found, otherwise None.
    :rtype: flaskLoginUser or None
    """
    print(user_id)
    user = User.query.filter_by(email=user_id).first() 
    if user:
        return flaskLoginUser(user.email,role=user.role, organization=user.organization.name)  # Or return a custom user object if needed
    return None

# Login route
@auth_bp.route("/api/login", methods=["POST", "GET"])
def login():
    """
    Log in a user using credentials provided in the form data.

    For POST requests, validates the user's username and password against the database.
    If authentication is successful, logs in the user using flask_login.

    """
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
@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    """
    Log out the currently authenticated user.

    """
    print(f"Current user authenticated: {current_user.is_authenticated}")  # Debugging
    print(f"Current user: {current_user}")
    if current_user.is_authenticated:
        logout_user()
        return jsonify({"message": "Logged out successfully"}), 200
    return jsonify({"error": "No user is logged in"}), 400

# User info route
@auth_bp.route("/api/user", methods=["GET"])
@login_required
def get_user_info():
    """
    Retrieve information about the currently authenticated user.

    """
    return jsonify({
        "username": current_user.id,
        "organization": current_user.organization,
        "email": current_user.id,
        "role": current_user.role
    }), 200

@auth_bp.route('/verify_old_password', methods=['POST'])
@login_required
def verify_old_password():
    """
    Verify that the old password provided by the user matches the stored password hash.

    Expects the old password to be sent in the form data as 'oldPassword'.

    """
    old_password = request.form.get("oldPassword")
    email = current_user.id

    # Get the current user's password hash
    user = User.query.filter_by(email=email).first() 
    print(user)

    # Check if the old password matches the stored hash
    if not check_password_hash(user.password, old_password):
        return jsonify({"error": "Old password is incorrect"}), 400

    return jsonify({"message": "Old password is correct"}), 200

@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """
    Change the password of the currently authenticated user.

    Expects the new password to be provided in the form data as 'newPassword'.
    The new password is hashed before storing in the database.

    """
    new_password = request.form.get("newPassword")
    email = current_user.id

    # Hash the new password before storing it
    user = User.query.filter_by(email=email).first() 
    user.password = generate_password_hash(new_password)

    db.session.commit()

    return jsonify({"message": "Password changed successfully!"}), 200

# Test authentication route
@auth_bp.route("/api/test", methods=["GET"])
def test_route():
    """
    A test endpoint to verify if a user is authenticated.

    """
    if not current_user.is_authenticated:
        return jsonify({"message": "User not authenticated"}), 401
    return jsonify({"message": "User is authenticated!"}), 200