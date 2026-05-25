from flask import Blueprint, jsonify, request, Flask
from flask_sqlalchemy import SQLAlchemy

# initialize DB without app binding first to avoid circular import
db = SQLAlchemy()
users_bp = Blueprint("users", __name__)


# create user model
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

# Create new user
@users_bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    username = data.get('username')

    if not data or 'username' not in data:
        return jsonify({"error": "Missing username"}), 400

    # Check if the username is already taken
    existing_user = db.session.query(User).filter_by(username=username).first()
    if existing_user:
        return jsonify({"error": f"Username '{username}' is already taken"}), 400
    new_user = User(username=data['username'])

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "id": new_user.id,
        "username": new_user.username
    }), 201

# Get all users
@users_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([
        {"id": u.id, "username": u.username}
        for u in users
    ])

# Get user by id
@users_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id": user.id,
        "username": user.username
    }), 200

# Update user
@users_bp.route('/users/update/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if 'username' in data:
        user.username = data['username']

    db.session.commit()
    return jsonify({"id": user.id}, {"username": user.username})

# delete user
@users_bp.route('/users/delete/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": f"User {user_id} deleted successfully"}), 200


    