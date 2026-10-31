from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models import (
    Booking,
    BookingStatus,
    Guest,
    RequestStatus,
    RequestType,
    Room,
    RoomStatus,
    ServiceRequest,
)


# =========================================================
# AVAILABILITY
# =========================================================

def find_available_rooms(
    db: Session,
    hotel_id: int,
    room_type: str,
    check_in: date,
    check_out: date,
) -> list[Room]:

    if check_out <= check_in:
        return []

    overlapping_booking = (
        select(
            Booking.room_id
        )
        .where(
            Booking.hotel_id
            == hotel_id,

            Booking.status.in_(
                [
                    BookingStatus.confirmed,
                    BookingStatus.checked_in,
                ]
            ),

            Booking.check_in
            < check_out,

            Booking.check_out
            > check_in,
        )
    )

    stmt = (
        select(
            Room
        )
        .where(
            Room.hotel_id
            == hotel_id,

            func.lower(
                Room.room_type
            )
            == room_type.lower(),

            Room.status
            != RoomStatus.maintenance,

            Room.id.not_in(
                overlapping_booking
            ),
        )
        .order_by(
            Room.price_per_night.asc()
        )
    )

    return list(
        db.scalars(
            stmt
        ).all()
    )


# =========================================================
# GUEST
# =========================================================

def get_or_create_guest(
    db: Session,
    name: str,
    email: str,
) -> Guest:

    guest = db.scalar(
        select(
            Guest
        ).where(
            func.lower(
                Guest.email
            )
            == email.lower()
        )
    )

    if guest:

        if (
            name
            and
            guest.name != name
        ):
            guest.name = name

        return guest

    guest = Guest(
        name=name,
        email=email,
    )

    db.add(
        guest
    )

    db.flush()

    return guest


# =========================================================
# CREATE BOOKING
# =========================================================

def create_booking(
    db: Session,
    hotel_id: int,
    guest_name: str,
    guest_email: str,
    room_type: str,
    check_in: date,
    check_out: date,
) -> Booking | None:

    if check_in < date.today():
        return None

    if check_out <= check_in:
        return None

    rooms = find_available_rooms(
        db,
        hotel_id,
        room_type,
        check_in,
        check_out,
    )

    if not rooms:
        return None

    room = rooms[0]

    guest = get_or_create_guest(
        db,
        guest_name,
        guest_email,
    )

    nights = (
        check_out
        - check_in
    ).days

    total = (
        Decimal(
            str(
                room.price_per_night
            )
        )
        * nights
    )

    booking = Booking(
        hotel_id=hotel_id,
        guest_id=guest.id,
        room_id=room.id,
        check_in=check_in,
        check_out=check_out,
        total_amount=total,
        status=
            BookingStatus.confirmed,
    )

    db.add(
        booking
    )

    db.commit()

    db.refresh(
        booking
    )

    return booking


# =========================================================
# CANCEL BOOKING
# =========================================================

def cancel_booking(
    db: Session,
    booking_id: int,
    guest_email: str,
) -> bool:

    booking = db.scalar(
        select(
            Booking
        )
        .join(
            Guest
        )
        .where(
            Booking.id
            == booking_id,

            func.lower(
                Guest.email
            )
            == guest_email.lower(),
        )
    )

    if not booking:
        return False

    if (
        booking.status
        == BookingStatus.cancelled
    ):
        return False

    booking.status = (
        BookingStatus.cancelled
    )

    db.commit()

    return True


# =========================================================
# EXTEND BOOKING
# =========================================================

def extend_booking(
    db: Session,
    booking_id: int,
    guest_email: str,
    new_check_out: date,
) -> tuple[
    Booking | None,
    str,
]:

    booking = db.scalar(
        select(
            Booking
        )
        .join(
            Guest
        )
        .where(
            Booking.id
            == booking_id,

            func.lower(
                Guest.email
            )
            == guest_email.lower(),
        )
    )

    if not booking:
        return (
            None,
            "not_found",
        )

    if booking.status not in [
        BookingStatus.confirmed,
        BookingStatus.checked_in,
    ]:
        return (
            None,
            "inactive",
        )

    if (
        new_check_out
        <= booking.check_out
    ):
        return (
            None,
            "invalid_date",
        )

    conflicting_booking = (
        db.scalar(
            select(
                Booking.id
            )
            .where(
                Booking.hotel_id
                == booking.hotel_id,

                Booking.room_id
                == booking.room_id,

                Booking.id
                != booking.id,

                Booking.status.in_(
                    [
                        BookingStatus.confirmed,
                        BookingStatus.checked_in,
                    ]
                ),

                Booking.check_in
                < new_check_out,

                Booking.check_out
                > booking.check_out,
            )
        )
    )

    if conflicting_booking:
        return (
            None,
            "unavailable",
        )

    room = db.get(
        Room,
        booking.room_id,
    )

    if not room:
        return (
            None,
            "room_not_found",
        )

    nights = (
        new_check_out
        - booking.check_in
    ).days

    booking.check_out = (
        new_check_out
    )

    booking.total_amount = (
        Decimal(
            str(
                room.price_per_night
            )
        )
        * nights
    )

    db.commit()

    db.refresh(
        booking
    )

    return (
        booking,
        "extended",
    )


# =========================================================
# OLD INTERNAL SERVICE REQUEST HELPER
# =========================================================

def create_service_request(
    db: Session,
    hotel_id: int,
    request_type: RequestType,
    description: str,
    room_number: str | None = None,
    guest_email: str | None = None,
) -> ServiceRequest:
    """
    Kept for backwards compatibility.

    The public AI tool no longer uses this.
    Public requests use
    create_verified_service_request().
    """

    room_id = None
    guest_id = None

    if room_number:

        room = db.scalar(
            select(
                Room
            ).where(
                Room.hotel_id
                == hotel_id,

                Room.number
                == room_number,
            )
        )

        if room:
            room_id = room.id

    if guest_email:

        guest = db.scalar(
            select(
                Guest
            ).where(
                func.lower(
                    Guest.email
                )
                == guest_email.lower()
            )
        )

        if guest:
            guest_id = guest.id

    item = ServiceRequest(
        hotel_id=hotel_id,
        room_id=room_id,
        guest_id=guest_id,
        request_type=
            request_type,
        description=
            description,
        status=
            RequestStatus.open,
    )

    db.add(
        item
    )

    db.commit()

    db.refresh(
        item
    )

    return item


# =========================================================
# SERVICE REQUEST BOOKING VERIFICATION
# =========================================================

def get_service_request_booking(
    db: Session,
    hotel_id: int,
    booking_id: int,
    guest_email: str,
    room_number: str | None = None,
) -> tuple[
    Booking | None,
    Guest | None,
    Room | None,
    str,
]:
    """
    Verify that:

    - booking exists
    - booking belongs to email
    - room belongs to booking
    - booking belongs to hotel
    - stay includes today
    """

    stmt = (
        select(
            Booking,
            Guest,
            Room,
        )
        .join(
            Guest,
            Booking.guest_id
            == Guest.id,
        )
        .join(
            Room,
            Booking.room_id
            == Room.id,
        )
        .where(
            Booking.id
            == booking_id,

            Booking.hotel_id
            == hotel_id,

            Room.hotel_id
            == hotel_id,

            func.lower(
                Guest.email
            )
            == guest_email
            .strip()
            .lower(),
        )
    )

    if room_number:

        stmt = stmt.where(
            Room.number
            == room_number.strip()
        )

    row = db.execute(
        stmt
    ).first()

    if not row:
        return (
            None,
            None,
            None,
            "not_found",
        )

    booking, guest, room = row

    if booking.status not in [
        BookingStatus.confirmed,
        BookingStatus.checked_in,
    ]:
        return (
            None,
            None,
            None,
            "inactive",
        )

    today = date.today()

    if not (
        booking.check_in
        <= today
        < booking.check_out
    ):
        return (
            None,
            None,
            None,
            "not_current_stay",
        )

    return (
        booking,
        guest,
        room,
        "verified",
    )


# =========================================================
# VERIFIED SERVICE REQUEST CREATION
# =========================================================

def create_verified_service_request(
    db: Session,
    hotel_id: int,
    booking_id: int,
    guest_email: str,
    request_type: RequestType,
    description: str,
    room_number: str | None = None,
) -> tuple[
    ServiceRequest | None,
    str,
]:

    (
        booking,
        guest,
        room,
        result,
    ) = get_service_request_booking(
        db,
        hotel_id=hotel_id,
        booking_id=booking_id,
        guest_email=guest_email,
        room_number=room_number,
    )

    if result != "verified":
        return (
            None,
            result,
        )

    item = ServiceRequest(
        hotel_id=hotel_id,
        room_id=room.id,
        guest_id=guest.id,
        request_type=
            request_type,
        description=
            description.strip(),
        status=
            RequestStatus.open,
    )

    db.add(
        item
    )

    db.commit()

    db.refresh(
        item
    )

    return (
        item,
        "created",
    )


# =========================================================
# STAFF DASHBOARD
# =========================================================

def list_bookings(
    db: Session,
    hotel_id: int,
) -> list[Booking]:

    stmt = (
        select(
            Booking
        )
        .options(
            joinedload(
                Booking.guest
            ),
            joinedload(
                Booking.room
            ),
        )
        .where(
            Booking.hotel_id
            == hotel_id
        )
        .order_by(
            Booking.created_at.desc()
        )
    )

    return list(
        db.scalars(
            stmt
        )
        .unique()
        .all()
    )


def list_service_requests(
    db: Session,
    hotel_id: int,
) -> list[ServiceRequest]:

    stmt = (
        select(
            ServiceRequest
        )
        .where(
            ServiceRequest.hotel_id
            == hotel_id
        )
        .order_by(
            ServiceRequest
            .created_at
            .desc()
        )
    )

    return list(
        db.scalars(
            stmt
        ).all()
    )


def get_dashboard_stats(
    db: Session,
    hotel_id: int,
) -> dict[
    str,
    int,
]:

    total_rooms = (
        db.scalar(
            select(
                func.count(
                    Room.id
                )
            ).where(
                Room.hotel_id
                == hotel_id
            )
        )
        or 0
    )

    available_rooms = (
        db.scalar(
            select(
                func.count(
                    Room.id
                )
            ).where(
                Room.hotel_id
                == hotel_id,

                Room.status
                == RoomStatus.available,
            )
        )
        or 0
    )

    active_bookings = (
        db.scalar(
            select(
                func.count(
                    Booking.id
                )
            ).where(
                Booking.hotel_id
                == hotel_id,

                Booking.status.in_(
                    [
                        BookingStatus.confirmed,
                        BookingStatus.checked_in,
                    ]
                ),
            )
        )
        or 0
    )

    open_requests = (
        db.scalar(
            select(
                func.count(
                    ServiceRequest.id
                )
            ).where(
                ServiceRequest.hotel_id
                == hotel_id,

                ServiceRequest.status.in_(
                    [
                        RequestStatus.open,
                        RequestStatus.in_progress,
                    ]
                ),
            )
        )
        or 0
    )

    return {
        "total_rooms":
            total_rooms,

        "available_rooms":
            available_rooms,

        "active_bookings":
            active_bookings,

        "open_service_requests":
            open_requests,
    }


def update_service_request_status(
    db: Session,
    request_id: int,
    status: RequestStatus,
) -> ServiceRequest | None:

    item = db.get(
        ServiceRequest,
        request_id,
    )

    if not item:
        return None

    item.status = status

    db.commit()

    db.refresh(
        item
    )

    return item