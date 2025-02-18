from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from project.utils.sql_models import db, User
from werkzeug.security import check_password_hash, generate_password_hash
import os
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user 
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_wtf import Form

# Create the blueprint
auth_bp = Blueprint('authentication', __name__)
website_name = os.environ.get("WEBSITE_NAME", "default_website_name")

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

# User loader function
@login_manager.user_loader
def load_user(user_id):
    print(user_id)
    user = User.query.filter_by(email=user_id).first() 
    if user:
        return flaskLoginUser(user.email,role=user.role, organization=user.organization.name)  # Or return a custom user object if needed
    return None

# Login route
@auth_bp.route("/api/login", methods=["POST", "GET"])
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
@auth_bp.route("/api/logout", methods=["POST"])
def logout():
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
    return jsonify({
        "username": current_user.id,
        "organization": current_user.organization,
        "email": current_user.id,
        "role": current_user.role
    }), 200

@auth_bp.route('/verify_old_password', methods=['POST'])
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

@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
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
    if not current_user.is_authenticated:
        return jsonify({"message": "User not authenticated"}), 401
    return jsonify({"message": "User is authenticated!"}), 200