from flask import request
from flask_restful import Resource

from config import db
from models import StageZone
from resources.decorators import admin_required


class StageZoneListResource(Resource):
    def get(self):
        # pagination
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        pagination = StageZone.query.order_by(StageZone.zone_id).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "zones": [z.to_dict() for z in pagination.items],
            "meta": {
                "total": pagination.total,
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_pages": pagination.pages,
            },
        }, 200

    @admin_required
    def post(self):
        data = request.get_json() or {}

        required = ("zone_name", "max_capacity")
        missing = [f for f in required if data.get(f) is None]
        if missing:
            return {"error": f"Missing required field(s): {', '.join(missing)}"}, 400

        try:
            zone = StageZone(
                zone_name=data["zone_name"],
                max_capacity=data["max_capacity"],
                vip_access=data.get("vip_access", False),
            )
            db.session.add(zone)
            db.session.commit()
        except ValueError as e:
            db.session.rollback()
            return {"error": str(e)}, 400

        return zone.to_dict(), 201


class StageZoneResource(Resource):
    def get(self, zone_id):
        zone = StageZone.query.get(zone_id)
        if not zone:
            return {"error": "Stage zone not found"}, 404
        return zone.to_dict(), 200

    @admin_required
    def patch(self, zone_id):
        zone = StageZone.query.get(zone_id)
        if not zone:
            return {"error": "Stage zone not found"}, 404

        data = request.get_json() or {}
        try:
            for field in ("zone_name", "max_capacity", "vip_access"):
                if field in data:
                    setattr(zone, field, data[field])
            db.session.commit()
        except ValueError as e:
            db.session.rollback()
            return {"error": str(e)}, 400

        return zone.to_dict(), 200

    @admin_required
    def delete(self, zone_id):
        zone = StageZone.query.get(zone_id)
        if not zone:
            return {"error": "Stage zone not found"}, 404

        db.session.delete(zone)
        db.session.commit()
        return {}, 204