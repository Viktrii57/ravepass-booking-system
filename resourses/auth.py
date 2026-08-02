from flask import request
from flask_restful import Resource
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

from config import db
from models import Fan


class Register(Resource):
    def post(self):
        data = request.get_json() or {}

        required = ("first_name", "last_name", "email", "password")
        missing = [f for f in required if not data.get(f)]
        if missing:
            return {"error": f"Missing required field(s): {', '.join(missing)}"}, 400

        # role defaults to 'fan'; only allow 'admin' if explicitly passed
        # (in a real app you'd lock this down further — e.g. invite-only admin creation)
        role = data.get("role", "fan")
        if role not in ("fan", "admin"):
            return {"error": "role must be 'fan' or 'admin'"}, 400

        try:
            fan = Fan(
                first_name=data["first_name"],
                last_name=data["last_name"],
                email=data["email"],
                phone=data.get("phone"),
                role=role,
            )
            fan.password_hash = data["password"]  # runs the bcrypt/werkzeug hash

            db.session.add(fan)
            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            return {"error": "An account with that email already exists"}, 409
        except ValueError as e:
            db.session.rollback()
            return {"error": str(e)}, 400

        token = create_access_token(
            identity=str(fan.fan_id),
            additional_claims={"role": fan.role},
        )

        return {
            "token": token,
            "fan": fan.to_dict(rules=("-bookings", "-wristband")),
        }, 201


class Login(Resource):
    def post(self):
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return {"error": "email and password are required"}, 400

        fan = Fan.query.filter_by(email=email).first()

        if not fan or not fan.authenticate(password):
            return {"error": "Invalid email or password"}, 401

        token = create_access_token(
            identity=str(fan.fan_id),
            additional_claims={"role": fan.role},
        )

        return {
            "token": token,
            "fan": fan.to_dict(rules=("-bookings", "-wristband")),
        }, 200