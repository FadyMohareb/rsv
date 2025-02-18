from flask import Blueprint, jsonify, request,abort, current_app
from functools import wraps
from flask_login import current_user, login_required
from project.utils.sql_models import db, User, Distribution, Organization
from werkzeug.security import generate_password_hash
import os, string, secrets, redis
from sqlalchemy.orm.attributes import flag_modified
from flask_mail import Message, Mail

# Create the blueprint
admin_bp = Blueprint('admin', __name__)
website_name = os.environ.get("WEBSITE_NAME", "default_website_name")
mail=Mail()

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

@admin_bp.route('/api/distributions_participants', methods=['GET'])
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

@admin_bp.route('/api/assign_participant', methods=['POST'])
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


@admin_bp.route("/api/create_distributions", methods=["GET", "POST"], strict_slashes=False)
@login_required
@role_required_for_post("superuser")
def distribution_manager():
    if request.method == "GET":
        # Fetch all distributions from the database
        distributions = Distribution.query.filter(Distribution.organizations.any(name=current_user.organization)).all()
        print(distributions)
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


@admin_bp.route("/api/create_or_restore_organization", methods=["POST"], strict_slashes=False)
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
    redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(redis_url)
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

    
@admin_bp.route("/api/distributions/<distribution>/add_samples", methods=["GET", "POST"], strict_slashes=False)
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
