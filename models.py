from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


1. FAN MODEL ( 1: 1 with wristband, 1: Many with ticketbooking)

class Fan(db.Model, SerializerMixin):
    __tablename__ = 'fans'

    # Exclude password_hash and reverse relationships to prevent infinite circular JSON loops
    serialize_rules = ('-password_hash', '-wristband.fan', '-ticket_bookings.fan')

    # Primary Key matching handwritten ERD: fan_id
    fan_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    # Secure Authentication Fields
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'user' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # RELATIONSHIP 1: 1:1 Relationship (Fan <-> Wristband)
    # uselist=False tells SQLAlchemy that a Fan only links to ONE Wristband object
    # cascade='all, delete-orphan' ensures deleting a Fan removes their issued Wristband
    wristband = db.relationship('Wristband', backref='fan', uselist=False, cascade='all, delete-orphan')

    # RELATIONSHIP 2: 1:Many Relationship (Fan -> TicketBooking)
    # One fan can create multiple ticket bookings over time
    ticket_bookings = db.relationship('TicketBooking', backref='fan', cascade='all, delete-orphan')

    # Helper functions to hash and verify passwords securely
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Fan {self.email} (ID: {self.fan_id})>'

# ========================================================================================================================

2. WRISTBAND MODEL (Access Pass, 1: 1 with fan)

class Wristband(db.Model, SerializerMixin):
    __tablename__ = 'wristbands'

    serialize_rules = ('-fan.wristband',)

    # Primary Key matching handwritten ERD: wristband_id
    wristband_id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key linking to Fan entity
    # Unique=True enforces the strict 1:1 database constraint!
    fan_id = db.Column(db.Integer, db.ForeignKey('fans.fan_id'), unique=True, nullable=False)
    
    # Chip code matching handwritten ERD: chip_code (RFID tag value)
    chip_code = db.Column(db.String(64), unique=True, nullable=False)
    
    activation_status = db.Column(db.String(20), nullable=False, default='Active')  # 'Active', 'Disabled'
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Wristband ID:{self.wristband_id} Chip:{self.chip_code}>'


# ========================================================================================================================

3. STAGE_ZONE MODEL (Festival Stage/Zones, 1:Many with PerformanceSlot)

class StageZone(db.Model, SerializerMixin):
    __tablename__ = 'stage_zones'

    serialize_rules = ('-performance_slots.stage_zone',)

    # Primary Key matching handwritten ERD: zone_id
    zone_id = db.Column(db.Integer, primary_key=True)
    zone_name = db.Column(db.String(80), nullable=False, unique=True)  # e.g., 'Sahara Tent'
    max_capacity = db.Column(db.Integer, nullable=False)

    # RELATIONSHIP 3: 1:M Relationship (StageZone -> PerformanceSlots) 
    # One stage zone hosts many scheduled performance slots across the festival weekend
    performance_slots = db.relationship('PerformanceSlot', backref='stage_zone', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<StageZone {self.zone_name} (Capacity: {self.max_capacity})>'


# ========================================================================================================================


4. PERFORMANCE_SLOT MODEL (Artist Scheduled Performance, 1:Many with TicketBooking)

class PerformanceSlot(db.Model, SerializerMixin):
    __tablename__ = 'performance_slots'

    serialize_rules = ('-stage_zone.performance_slots', '-ticket_bookings.performance_slot')

    # Primary Key matching handwritten ERD: slot_id
    slot_id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key pointing to the stage zone hosting the performance
    zone_id = db.Column(db.Integer, db.ForeignKey('stage_zones.zone_id'), nullable=False)
    
    # Fields matching handwritten ERD
    artist_name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.String(10), nullable=False)  # e.g., '20:00'
    end_time = db.Column(db.String(10), nullable=False)    # e.g., '21:30'

    # 1:M Relationship -> PerformanceSlot -> TicketBookings
    ticket_bookings = db.relationship('TicketBooking', backref='performance_slot', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<PerformanceSlot {self.artist_name} at Zone ID:{self.zone_id}>'


# ========================================================================================================================


5. TICKET_BOOKING MODEL (Fan Ticket Booking, Many:1 with Fan and PerformanceSlot)

class TicketBooking(db.Model, SerializerMixin):
    __tablename__ = 'ticket_bookings'

    serialize_rules = ('-fan.ticket_bookings', '-performance_slot.ticket_bookings')

    # Primary Key matching handwritten ERD: booking_id
    booking_id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys connecting the Many:Many pair (Fan <-> PerformanceSlot)
    fan_id = db.Column(db.Integer, db.ForeignKey('fans.fan_id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('performance_slots.slot_id'), nullable=False)
    
    # --- EXTRA JOIN ATTRIBUTES / PAYLOAD ---
    # These attributes justify why this is an association object rather than a plain join table!
    tier_name = db.Column(db.String(30), nullable=False, default='General Admission')  # e.g., 'GA', 'VIP'
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    booking_status = db.Column(db.String(20), nullable=False, default='Confirmed')  # 'Confirmed', 'Cancelled'
    booked_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TicketBooking ID:{self.booking_id} Fan:{self.fan_id} Slot:{self.slot_id}>'