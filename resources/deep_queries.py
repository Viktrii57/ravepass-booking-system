from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from config import db
from models import TicketBooking, PerformanceSlot, StageZone, Fan
from resources.decorators import admin_required


class ZoneRevenueResource(Resource):
    """
    DEEP QUERY 1 — Aggregation across a 3-table join.
    Total confirmed-booking revenue per stage zone.

    Join: ticket_bookings -> performance_slots -> stage_zones
    Aggregate: func.sum(unit_price), func.count(booking_id), group_by zone
    """

    @admin_required
    def get(self):
        results = (
            db.session.query(
                StageZone.zone_id,
                StageZone.zone_name,
                func.count(TicketBooking.booking_id).label("ticket_count"),
                func.sum(TicketBooking.unit_price).label("total_revenue"),
            )
            .join(PerformanceSlot, PerformanceSlot.zone_id == StageZone.zone_id)
            .join(TicketBooking, TicketBooking.slot_id == PerformanceSlot.slot_id)
            .filter(TicketBooking.booking_status == "confirmed")
            .group_by(StageZone.zone_id, StageZone.zone_name)
            .having(func.count(TicketBooking.booking_id) > 0)
            .order_by(func.sum(TicketBooking.unit_price).desc())
            .all()
        )

        return {
            "zone_revenue": [
                {
                    "zone_id": r.zone_id,
                    "zone_name": r.zone_name,
                    "ticket_count": r.ticket_count,
                    "total_revenue": float(r.total_revenue),
                }
                for r in results
            ]
        }, 200


class SlotAttendeesResource(Resource):
    """
    DEEP QUERY 2 — Join across the association object to the "far side"
    of the many:many, with a status filter and pagination.

    Join: performance_slots -> ticket_bookings -> fans
    Filter: ?status=confirmed (default) — booking_status
    Admin-only: exposes fan PII (name/email), so not public.
    """

    @admin_required
    def get(self, slot_id):
        slot = PerformanceSlot.query.get(slot_id)
        if not slot:
            return {"error": "Performance slot not found"}, 404

        status_filter = request.args.get("status", "confirmed")
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        query = (
            db.session.query(TicketBooking)
            .join(Fan, TicketBooking.fan_id == Fan.fan_id)
            .options(joinedload(TicketBooking.fan))
            .filter(
                TicketBooking.slot_id == slot_id,
                TicketBooking.booking_status == status_filter,
            )
            .order_by(Fan.last_name, Fan.first_name)
        )

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "slot": {"slot_id": slot.slot_id, "artist_name": slot.artist_name},
            "attendees": [
                {
                    "fan_id": b.fan.fan_id,
                    "first_name": b.fan.first_name,
                    "last_name": b.fan.last_name,
                    "email": b.fan.email,
                    "tier_name": b.tier_name,
                    "booking_status": b.booking_status,
                }
                for b in pagination.items
            ],
            "meta": {
                "total": pagination.total,
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_pages": pagination.pages,
            },
        }, 200


class FanScheduleResource(Resource):
    """
    DEEP QUERY 3 — Relationship filter via .has(), plus a join for
    eager-loaded zone info. The logged-in fan's upcoming, confirmed
    bookings, ordered chronologically.

    .has() demonstrates filtering PerformanceSlot by a condition on its
    OWN related StageZone (a filter across a relationship), while the
    booking query itself joins slot -> zone via joinedload to avoid N+1.
    """

    @jwt_required()
    def get(self):
        fan_id = get_jwt_identity()

        vip_only = request.args.get("vip_only", "false").lower() == "true"

        query = (
            TicketBooking.query.join(PerformanceSlot)
            .options(joinedload(TicketBooking.performance_slot).joinedload(PerformanceSlot.stage_zone))
            .filter(
                TicketBooking.fan_id == fan_id,
                TicketBooking.booking_status == "confirmed",
            )
        )

        if vip_only:
            # .has() -> filter PerformanceSlot rows by a condition on their
            # related StageZone, without a separate explicit join clause
            query = query.filter(
                PerformanceSlot.stage_zone.has(StageZone.vip_access == True)  # noqa: E712
            )

        bookings = query.order_by(
            PerformanceSlot.performance_date, PerformanceSlot.start_time
        ).all()

        return {
            "schedule": [
                {
                    "booking_id": b.booking_id,
                    "tier_name": b.tier_name,
                    "artist_name": b.performance_slot.artist_name,
                    "performance_date": str(b.performance_slot.performance_date),
                    "start_time": str(b.performance_slot.start_time),
                    "zone_name": b.performance_slot.stage_zone.zone_name,
                    "vip_access": b.performance_slot.stage_zone.vip_access,
                }
                for b in bookings
            ]
        }, 200