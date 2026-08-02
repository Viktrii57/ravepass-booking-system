from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError

from config import db
from models import Wristband, Fan
from resources.decorators import admin_required


class WristbandResource(Resource):
    """
    Self-service endpoint for the CURRENTLY LOGGED-IN fan's own wristband.
    No <id> in the URL — identity comes from the JWT, which is what makes
    this a true 1:1 lookup ("give me MY wristband") rather than a generic
    by-id fetch.
    """

    @jwt_required()
    def get(self):
        fan_id = get_jwt_identity()
        fan = Fan.query.get(fan_id)

        if not fan.wristband:
            return {"error": "No wristband issued yet"}, 404

        return fan.wristband.to_dict(), 200

    @jwt_required()
    def post(self):
        fan_id = get_jwt_identity()
        fan = Fan.query.get(fan_id)

        # enforce the 1:1 in application logic too, not just the DB constraint —
        # gives a clean 409 instead of a raw IntegrityError
        if fan.wristband:
            return {"error": "This fan already has a wristband"}, 409

        data = request.get_json() or {}
        chip_code = data.get("chip_code")
        if not chip_code:
            return {"error": "chip_code is required"}, 400

        try:
            wristband = Wristband(
                fan_id=fan.fan_id,
                chip_code=chip_code,
                activation_status="inactive",  # always starts inactive; admin activates at gate
            )
            db.session.add(wristband)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {"error": "That chip_code is already in use"}, 409
        except ValueError as e:
            db.session.rollback()
            return {"error": str(e)}, 400

        return wristband.to_dict(), 201


class AdminWristbandActivateResource(Resource):
    """
    Staff-facing endpoint: activate (or update the status of) any fan's
    wristband by wristband_id — e.g. scanning it at the gate.
    """

    @admin_required
    def patch(self, wristband_id):
        wristband = Wristband.query.get(wristband_id)
        if not wristband:
            return {"error": "Wristband not found"}, 404

        data = request.get_json() or {}
        status = data.get("activation_status")
        if not status:
            return {"error": "activation_status is required"}, 400

        try:
            wristband.activation_status = status
            db.session.commit()
        except ValueError as e:
            db.session.rollback()
            return {"error": str(e)}, 400

        return wristband.to_dict(), 200