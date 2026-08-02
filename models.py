from datetime import datetime, date
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.associationproxy import association_proxy
from werkzeug.security import generate_password_hash, check_password_hash

from config import db



# FAN  (doubles as the auth "User" — role-based: 'fan' or 'admin')

class Fan(db.Model, SerializerMixin):
    __tablename__ = "fans"

    # keep nested serialization shallow to avoid recursion:
    # fan -> wristband (ok), fan -> bookings -> slot (ok), don't go back up
    serialize_rules = (
        "-bookings.fan",
        "-wristband.fan",
        "-_password_hash",
    )

    fan_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)
    phone = db.Column(db.String)

    _password_hash = db.Column("password_hash", db.String, nullable=False)
    role = db.Column(db.String, nullable=False, default="fan")  # 'fan' | 'admin'

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # 1:1  Fan <-> Wristband
    wristband = db.relationship(
        "Wristband",
        back_populates="fan",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # many:many  Fan <-> PerformanceSlot  via TicketBooking (association object)
    bookings = db.relationship(
        "TicketBooking",
        back_populates="fan",
        cascade="all, delete-orphan",
    )
    performance_slots = association_proxy("bookings", "performance_slot")

    # password handling 
    @hybrid_property
    def password_hash(self):
        raise AttributeError("password_hash is not directly readable")

    @password_hash.setter
    def password_hash(self, password):
        self._password_hash = generate_password_hash(password)

    def authenticate(self, password):
        return check_password_hash(self._password_hash, password)

    @validates("email")
    def validate_email(self, key, email):
        if "@" not in email:
            raise ValueError("Invalid email address")
        return email

    @validates("role")
    def validate_role(self, key, role):
        if role not in ("fan", "admin"):
            raise ValueError("role must be 'fan' or 'admin'")
        return role

    def __repr__(self):
        return f"<Fan {self.fan_id} {self.email} ({self.role})>"



# WRISTBAND  (1:1 with Fan)

class Wristband(db.Model, SerializerMixin):
    __tablename__ = "wristbands"

    serialize_rules = ("-fan.wristband",)

    wristband_id = db.Column(db.Integer, primary_key=True)
    fan_id = db.Column(db.Integer, db.ForeignKey("fans.fan_id"), nullable=False, unique=True)
    chip_code = db.Column(db.String, nullable=False, unique=True)
    activation_status = db.Column(db.String, nullable=False, default="inactive")  # inactive | active | lost

    fan = db.relationship("Fan", back_populates="wristband")

    @validates("activation_status")
    def validate_status(self, key, value):
        if value not in ("inactive", "active", "lost"):
            raise ValueError("activation_status must be inactive, active, or lost")
        return value

    def __repr__(self):
        return f"<Wristband {self.wristband_id} chip={self.chip_code} status={self.activation_status}>"



# STAGE ZONE  (1:many -> PerformanceSlot)

class StageZone(db.Model, SerializerMixin):
    __tablename__ = "stage_zones"

    serialize_rules = ("-performance_slots.stage_zone",)

    zone_id = db.Column(db.Integer, primary_key=True)
    zone_name = db.Column(db.String, nullable=False)
    max_capacity = db.Column(db.Integer, nullable=False)
    vip_access = db.Column(db.Boolean, default=False)

    # 1:many  StageZone -> PerformanceSlot
    performance_slots = db.relationship(
        "PerformanceSlot",
        back_populates="stage_zone",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<StageZone {self.zone_id} {self.zone_name} cap={self.max_capacity}>"



# PERFORMANCE SLOT (belongs to StageZone; many:many with Fan via TicketBooking)

class PerformanceSlot(db.Model, SerializerMixin):
    __tablename__ = "performance_slots"

    serialize_rules = (
        "-stage_zone.performance_slots",
        "-bookings.performance_slot",
    )

    slot_id = db.Column(db.Integer, primary_key=True)
    artist_name = db.Column(db.String, nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey("stage_zones.zone_id"), nullable=False)
    performance_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    stage_zone = db.relationship("StageZone", back_populates="performance_slots")

    # many:many  PerformanceSlot <-> Fan  via TicketBooking
    bookings = db.relationship(
        "TicketBooking",
        back_populates="performance_slot",
        cascade="all, delete-orphan",
    )
    fans = association_proxy("bookings", "fan")

    @validates("end_time")
    def validate_time_order(self, key, end_time):
        if self.start_time and end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return end_time

    def __repr__(self):
        return f"<PerformanceSlot {self.slot_id} {self.artist_name} @ zone {self.zone_id}>"



# TICKET BOOKING (association object: Fan <-> PerformanceSlot)

class TicketBooking(db.Model, SerializerMixin):
    __tablename__ = "ticket_bookings"

    serialize_rules = (
        "-fan.bookings",
        "-performance_slot.bookings",
    )

    booking_id = db.Column(db.Integer, primary_key=True)
    fan_id = db.Column(db.Integer, db.ForeignKey("fans.fan_id"), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey("performance_slots.slot_id"), nullable=False)

    tier_name = db.Column(db.String, nullable=False)       # e.g. General, VIP, Backstage
    unit_price = db.Column(db.Numeric(8, 2), nullable=False)
    booking_status = db.Column(db.String, nullable=False, default="confirmed")  # confirmed | cancelled | waitlisted
    booked_at = db.Column(db.DateTime, server_default=db.func.now())

    fan = db.relationship("Fan", back_populates="bookings")
    performance_slot = db.relationship("PerformanceSlot", back_populates="bookings")

    __table_args__ = (
        db.UniqueConstraint("fan_id", "slot_id", "tier_name", name="uq_fan_slot_tier"),
    )

    @validates("booking_status")
    def validate_status(self, key, value):
        if value not in ("confirmed", "cancelled", "waitlisted"):
            raise ValueError("booking_status must be confirmed, cancelled, or waitlisted")
        return value

    def __repr__(self):
        return f"<TicketBooking {self.booking_id} fan={self.fan_id} slot={self.slot_id} {self.booking_status}>"