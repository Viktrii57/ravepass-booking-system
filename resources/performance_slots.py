from datetime import datetime

from flask import request
from flask_restful import Resource
from sqlalchemy.orm import joinedload

from config import db
from models import PerformanceSlot, StageZone
from resources.decorators import admin_required


def _parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_time(value):
    return datetime.strptime(value, "%H:%M").time()


class PerformanceSlotListResource(Resource):
    def get(self):
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        # eager-load stage_zone to avoid an N+1 query per slot when serializing
        query = PerformanceSlot.query.options(joinedload(PerformanceSlot.stage_zone))

        # optional filter: /performance_slots?zone_id=2
        zone_id = request.args.get("zone_id", type=int)
        if zone_id:
            query = query.filter(PerformanceSlot.zone_id == zone_id)

        pagination = query.order_by(
            PerformanceSlot.performance_date, PerformanceSlot.start_time
        ).paginate(page=page, per_page=per_page, error_out=False)

        return {
            "performance_slots": [s.to_dict() for s in pagination.items],
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

        required = ("artist_name", "zone_id", "performance_date", "start_time", "end_time")
        missing = [f for f in required if data.get(f) is None]
        if missing:
            return {"error": f"Missing required field(s): {', '.join(missing)}"}, 400

        # FK integrity check — fail clean with 404, not a DB-level foreign key error
        zone = StageZone.query.get(data["zone_id"])
        if not zone:
            return {"error": f"Stage zone {data['zone_id']} does not exist"}, 404

        try:
            slot = PerformanceSlot(
                artist_name=data["artist_name"],
                zone_id=data["zone_id"],
                performance_date=_parse_date(data["performance_date"]),
                start_time=_parse_time(data["start_time"]),
                end_time=_parse_time(data["end_time"]),
            )
            db.session.add(slot)
            db.session.commit()
        except ValueError as e:
            db.session.rollback()
            return {"error": str(e)}, 400

        return slot.to_dict(), 201


class PerformanceSlotResource(Resource):
    def get(self, slot_id):
        slot = PerformanceSlot.query.get(slot_id)
        if not slot:
            return {"error": "Performance slot not found"}, 404
        return slot.to_dict(), 200

    @admin_required
    def patch(self, slot_id):
        slot = PerformanceSlot.query.get(slot_id)
        if not slot:
            return {"error": "Performance slot not found"}, 404

        data = request.get_json() or {}

        if "zone_id" in data:
            zone = StageZone.query.get(data["zone_id"])
            if not zone:
                return {"error": f"Stage zone {data['zone_id']} does not exist"}, 404
            slot.zone_id = data["zone_id"]

        try:
            if "artist_name" in data:
                slot.artist_name = data["artist_name"]
            if "performance_date" in data:
                slot.performance_date = _parse_date(data["performance_date"])
            if "start_time" in data:
                slot.start_time = _parse_time(data["start_time"])
            if "end_time" in data:
                slot.end_time = _parse_time(data["end_time"])
            db.session.commit()
        except ValueError as e:
            db.session.rollback()
            return {"error": str(e)}, 400

        return slot.to_dict(), 200

    @admin_required
    def delete(self, slot_id):
        slot = PerformanceSlot.query.get(slot_id)
        if not slot:
            return {"error": "Performance slot not found"}, 404

        db.session.delete(slot)
        db.session.commit()
        return {}, 204