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


# Extensions (created here, initialized on the app in app.py)

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)

    # core config, all pulled from environment (.env, git-ignored)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URI")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")

    # dev convenience — for 6 hours, before a real deployment.
    from datetime import timedelta
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=6)

    # init extensions on the app 
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app)

    api = Api(app)

    # register resources 
    from resources.auth import Register, Login
    from resources.stage_zones import StageZoneListResource, StageZoneResource
    from resources.performance_slots import PerformanceSlotListResource, PerformanceSlotResource
    from resources.wristbands import WristbandResource, AdminWristbandActivateResource
    from resources.ticket_bookings import TicketBookingListResource, TicketBookingResource

    api.add_resource(Register, "/register")
    api.add_resource(Login, "/login")
    api.add_resource(StageZoneListResource, "/stage_zones")
    api.add_resource(StageZoneResource, "/stage_zones/<int:zone_id>")
    api.add_resource(PerformanceSlotListResource, "/performance_slots")
    api.add_resource(PerformanceSlotResource, "/performance_slots/<int:slot_id>")
    api.add_resource(WristbandResource, "/wristband")
    api.add_resource(AdminWristbandActivateResource, "/wristbands/<int:wristband_id>/activate")
    api.add_resource(TicketBookingListResource, "/bookings")
    api.add_resource(TicketBookingResource, "/bookings/<int:booking_id>")



    return app