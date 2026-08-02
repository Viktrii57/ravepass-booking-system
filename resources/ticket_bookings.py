from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy.exc import IntegrityError

from config import db
from models import TicketBooking, PerformanceSlot, Fan
from resources.decorators import admin_required


class TicketBookingListResource(Resource):
    @jwt_required()
    def get(self):
        """
        A fan sees only their own bookings.
        An admin can pass ?fan_id=<id> to inspect a specific fan's bookings,
        or omit it to see ALL bookings (still paginated).
        """
        claims = get_jwt()
        current_fan_id = get_jwt_identity()

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        query = TicketBooking.query

        if claims.get("role") == "admin":
            fan_id_filter = request.args.get("fan_id", type=int)
            if fan_id_filter:
                query = query.filter(TicketBooking.fan_id == fan_id_filter)
            # else: no filter -> admin sees every booking
        else:
            query = query.filter(TicketBooking.fan_id == current_fan_id)

        pagination = query.order_by(TicketBooking.booked_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "bookings": [b.to_dict() for b in pagination.items],
            "meta": {
                "total": pagination.total,
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_pages": pagination.pages,
            },
        }, 200

    @jwt_required()
    def post(self):
        fan_id = get_jwt_identity()

        data = request.get_json() or {}
        required = ("slot_id", "tier_name", "unit_price")
        missing = [f for f in required if data.get(f) is None]
        if missing:
            return {"error": f"Missing required field(s): {', '.join(missing)}"}, 400

        slot = PerformanceSlot.query.get(data["slot_id"])
        if not slot:
            return {"error": f"Performance slot {data['slot_id']} does not exist"}, 404

        try:
            booking = TicketBooking(
                fan_id=fan_id,
                slot_id=data["slot_id"],
                tier_name=data["tier_name"],
                unit_price=data["unit_price"],
                booking_status="confirmed",
            )
            db.session.add(booking)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {
                "error": "You already have a booking for this slot at this tier"
            }, 409
        except ValueError as e:
            db.session.rollback()
            return {"error": str(e)}, 400

        return booking.to_dict(), 201


class TicketBookingResource(Resource):
    @jwt_required()
    def get(self, booking_id):
        booking = TicketBooking.query.get(booking_id)
        if not booking:
            return {"error": "Booking not found"}, 404

        claims = get_jwt()
        current_fan_id = get_jwt_identity()
        if claims.get("role") != "admin" and str(booking.fan_id) != str(current_fan_id):
            return {"error": "You do not have access to this booking"}, 403

        return booking.to_dict(), 200

    @jwt_required()
    def patch(self, booking_id):
        """
        A fan can cancel their OWN booking (status -> 'cancelled').
        An admin can set any status on any booking.
        """
        booking = TicketBooking.query.get(booking_id)
        if not booking:
            return {"error": "Booking not found"}, 404

        claims = get_jwt()
        current_fan_id = get_jwt_identity()
        is_admin = claims.get("role") == "admin"
        is_owner = str(booking.fan_id) == str(current_fan_id)

        if not is_admin and not is_owner:
            return {"error": "You do not have access to this booking"}, 403

        data = request.get_json() or {}
        new_status = data.get("booking_status")
        if not new_status:
            return {"error": "booking_status is required"}, 400

        # a non-admin owner may only cancel — not flip to confirmed/waitlisted
        if not is_admin and new_status != "cancelled":
            return {"error": "You may only cancel your own booking"}, 403

        try:
            booking.booking_status = new_status
            db.session.commit()
        except ValueError as e:
            db.session.rollback()
            return {"error": str(e)}, 400

        return booking.to_dict(), 200