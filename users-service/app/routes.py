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

    if not data or 'username' not in data:
        return jsonify({"error": "Missing username"}), 400

    new_user = User(username=data['username'])

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "id": new_user.id,
        "username": new_user.username
    }), 201

@users_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([
        {"id": u.id, "username": u.username}
        for u in users
    ])

