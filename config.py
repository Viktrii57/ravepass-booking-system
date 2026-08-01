import os
from dotenv import load_dotenv

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_bcrypt import Bcrypt

load_dotenv()

# ---------------------------------------------------------------------------
# Extensions (created here, initialized on the app in app.py)
# ---------------------------------------------------------------------------
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)

    # --- core config, all pulled from environment (.env, git-ignored) -----
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URI"
    ) or "sqlite:///ravepass.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "dev-secret-key"
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY") or "dev-jwt-secret"

    # --- init extensions on the app ----------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app)

    api = Api(app)

    # --- register resources here as you build them --------------------
    # from resources.auth import Register, Login
    # from resources.fans import FanListResource, FanResource
    # api.add_resource(Register, "/register")
    # api.add_resource(Login, "/login")

    return app