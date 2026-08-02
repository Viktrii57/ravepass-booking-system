import random
from datetime import date, time, timedelta

from faker import Faker

from config import create_app, db
from models import Fan, Wristband, StageZone, PerformanceSlot, TicketBooking

fake = Faker()

# Festival-appropriate constants — real Faker data (names/emails) mixed with
# domain-appropriate fixed lists (nobody wants a stage zone called "Ltd Group")
ZONE_DATA = [
    ("Main Stage", 8000, True),
    ("Bass Arena", 4000, False),
    ("Chill Grove", 1500, False),
    ("Underground Tent", 2500, False),
    ("VIP Terrace", 600, True),
]

ARTIST_NAMES = [
    "Nova Wolfe", "The Midnight Static", "Kaia Reyes", "Solar Drift",
    "Echo Foundry", "DJ Halcyon", "Velvet Circuit", "The Amber Hours",
    "Rift Valley", "Juno Sparks", "Glass Horizon", "The Low End Theory",
    "Wraith & The Sirens", "Pulse Theory", "Marigold Static",
]

TIERS = [("General", 45.00), ("VIP", 120.00), ("Backstage", 250.00)]
BOOKING_STATUSES_WEIGHTED = (
    ["confirmed"] * 7 + ["waitlisted"] * 2 + ["cancelled"] * 1
)  # mostly confirmed, some variety


def clear_tables():
    """Delete in FK-safe order: children before parents."""
    TicketBooking.query.delete()
    Wristband.query.delete()
    PerformanceSlot.query.delete()
    StageZone.query.delete()
    Fan.query.delete()
    db.session.commit()


def seed_fans(n=20):
    fans = []

    # one guaranteed admin account, predictable credentials for testing
    admin = Fan(
        first_name="Admin",
        last_name="User",
        email="admin@ravepass.com",
        phone=fake.phone_number()[:20],
        role="admin",
    )
    admin.password_hash = "adminpass"
    fans.append(admin)

    for _ in range(n):
        fan = Fan(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.unique.email(),
            phone=fake.phone_number()[:20],
            role="fan",
        )
        fan.password_hash = "password123"
        fans.append(fan)

    db.session.add_all(fans)
    db.session.commit()
    return fans


def seed_wristbands(fans):
    wristbands = [
        Wristband(
            fan_id=fan.fan_id,
            chip_code=f"CHIP-{fan.fan_id:05d}-{fake.unique.random_number(digits=4)}",
            activation_status=random.choice(["inactive", "active", "active", "active"]),
        )
        for fan in fans
    ]
    db.session.add_all(wristbands)
    db.session.commit()
    return wristbands


def seed_stage_zones():
    zones = [
        StageZone(zone_name=name, max_capacity=cap, vip_access=vip)
        for name, cap, vip in ZONE_DATA
    ]
    db.session.add_all(zones)
    db.session.commit()
    return zones


def seed_performance_slots(zones, n=25):
    festival_start = date(2026, 9, 4)  # a Friday, three-day festival weekend
    slots = []

    for i in range(n):
        zone = random.choice(zones)
        day_offset = random.randint(0, 2)
        performance_date = festival_start + timedelta(days=day_offset)

        start_hour = random.randint(12, 22)
        start = time(hour=start_hour, minute=random.choice([0, 15, 30, 45]))
        end_hour = min(start_hour + random.choice([1, 2]), 23)
        end = time(hour=end_hour, minute=start.minute)

        slot = PerformanceSlot(
            artist_name=ARTIST_NAMES[i % len(ARTIST_NAMES)],
            zone_id=zone.zone_id,
            performance_date=performance_date,
            start_time=start,
            end_time=end,
        )
        slots.append(slot)

    db.session.add_all(slots)
    db.session.commit()
    return slots


def seed_ticket_bookings(fans, slots):
    # only regular fans book tickets (keep the admin account clean for testing)
    bookable_fans = [f for f in fans if f.role == "fan"]

    bookings = []
    seen_combos = set()  # (fan_id, slot_id, tier_name) — respect the UniqueConstraint

    for fan in bookable_fans:
        num_bookings = random.randint(1, 4)
        chosen_slots = random.sample(slots, k=min(num_bookings, len(slots)))

        for slot in chosen_slots:
            tier_name, base_price = random.choice(TIERS)
            combo = (fan.fan_id, slot.slot_id, tier_name)
            if combo in seen_combos:
                continue
            seen_combos.add(combo)

            booking = TicketBooking(
                fan_id=fan.fan_id,
                slot_id=slot.slot_id,
                tier_name=tier_name,
                unit_price=base_price,
                booking_status=random.choice(BOOKING_STATUSES_WEIGHTED),
            )
            bookings.append(booking)

    db.session.add_all(bookings)
    db.session.commit()
    return bookings


def run():
    app = create_app()
    with app.app_context():
        print("Clearing existing data...")
        clear_tables()

        print("Seeding fans...")
        fans = seed_fans(n=20)

        print("Seeding wristbands (1:1)...")
        seed_wristbands(fans)

        print("Seeding stage zones...")
        zones = seed_stage_zones()

        print("Seeding performance slots (1:many from stage zones)...")
        slots = seed_performance_slots(zones, n=25)

        print("Seeding ticket bookings (many:many, Fan <-> PerformanceSlot)...")
        bookings = seed_ticket_bookings(fans, slots)

        print("\nDone.")
        print(f"  Fans:              {len(fans)} (1 admin, {len(fans) - 1} regular)")
        print(f"  Wristbands:        {len(fans)}")
        print(f"  Stage zones:       {len(zones)}")
        print(f"  Performance slots: {len(slots)}")
        print(f"  Ticket bookings:   {len(bookings)}")
        print("\n  Admin login -> email: admin@ravepass.com  password: adminpass")
        print("  All seeded fans    -> password: password123")


if __name__ == "__main__":
    run()