from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.database import db
from app.models import User, AuditLog

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Endpoint for user registration."""
    data = request.get_json() or {}
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'Pharmacist')

    if not username or not email or not password:
        return jsonify({'message': 'Username, email, and password are required.'}), 400

    if role not in ['Pharmacist', 'Supervisor', 'Admin']:
        return jsonify({'message': 'Invalid role specified. Must be one of: Pharmacist, Supervisor, Admin.'}), 400

    # Check if user already exists
    if User.query.filter((User.username == username) | (User.email == email)).first():
        # Log failed registration attempt (security/audit check)
        log = AuditLog(
            action='REGISTRATION_FAILURE',
            details=f'Attempted registration with existing username: {username} or email: {email}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'message': 'Username or Email already registered.'}), 409

    try:
        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.flush()  # Populates new_user.id for the log

        # Log successful registration
        log = AuditLog(
            user_id=new_user.id,
            action='REGISTRATION_SUCCESS',
            details=f'User {username} successfully registered with role {role}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            'message': 'User registered successfully.',
            'user': new_user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'An error occurred during registration.', 'error': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Endpoint for user authentication, returning a JWT token on success."""
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required.'}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        # Log unauthorized login attempt
        log = AuditLog(
            user_id=user.id if user else None,
            action='LOGIN_FAILURE',
            details=f'Failed login attempt for username: {username}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'message': 'Invalid username or password.'}), 401

    # Log successful login
    log = AuditLog(
        user_id=user.id,
        action='LOGIN_SUCCESS',
        details=f'User {username} successfully authenticated.',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()

    # Create JWT access token
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'message': 'Login successful.',
        'access_token': access_token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Retrieve details of the currently logged-in user."""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'message': 'User not found.'}), 404
        
    return jsonify(user.to_dict()), 200
