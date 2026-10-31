from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

from app.db.session import SessionLocal
from app.models import RequestType, Room

from app.services.email_service import (
    get_department_name,
    send_booking_confirmation,
    send_booking_creation_otp,
    send_booking_verification_otp,
    send_service_request_otp,
    send_service_request_staff_notification,
)

from app.services.hotel_service import (
    cancel_booking as cancel_booking_service,
    create_booking as create_booking_service,
    create_verified_service_request as create_service_request_service,
    extend_booking as extend_booking_service,
    find_available_rooms,
    get_service_request_booking,
)

from app.services.rag_service import search_knowledge

from app.services.verification_service import (
    build_booking_request_hash,
    build_service_request_hash,
    create_booking_otp,
    create_email_otp,
    invalidate_latest_email_otp,
    invalidate_latest_otp,
    verify_booking_otp,
    verify_email_otp,
)


# DATE HELPERS

HOTEL_TIMEZONE = ZoneInfo("Asia/Kolkata")


def hotel_today() -> date:
    """
    Return today's date in hotel local time.
    """

    return datetime.now(HOTEL_TIMEZONE).date()


def parse_date_value(value: str) -> date:
    """
    Parse YYYY-MM-DD, today or tomorrow.
    """

    cleaned = (value.strip().lower())

    today = hotel_today()

    if cleaned == "today":
        return today

    if cleaned in {"tomorrow", "tommorow",}:
        return (today + timedelta(days=1))

    return date.fromisoformat(cleaned)


def validate_stay_dates(check_in: date, check_out: date) -> str | None:
    """
    Validate hotel stay dates.
    """

    today = hotel_today()

    if check_in < today:
        return (
            "Check-in cannot be in the past. "
            "Please provide today or a future "
            "check-in date."
        )

    if check_out <= check_in:
        return (
            "Check-out must be later "
            "than check-in."
        )

    return None


def parse_stay_dates(check_in: str, check_out: str) -> tuple[date | None, date | None, str | None]:
    """
    Parse and validate a hotel stay period.
    """

    if not check_in.strip() or not check_out.strip():
        return (
            None,
            None,
            (
                "Both check-in and check-out "
                "dates are required. Ask the "
                "guest to provide both dates. "
                "Do not assume or invent dates."
            ),
        )

    try:
        start = parse_date_value(check_in)
        end = parse_date_value(check_out)

    except ValueError:
        return (
            None,
            None,
            (
                "Invalid date. Use YYYY-MM-DD, "
                "today, or tomorrow."
            ),
        )

    error = validate_stay_dates(start, end)

    if error:
        return (
            None,
            None,
            error,
        )

    return (
        start,
        end,
        None,
    )



# GENERAL HELPERS

def normalize_room_type(room_type: str) -> str:
    """
    Normalize room type from guest wording.
    """

    value = (room_type.lower().strip())

    for known_type in ["standard", "deluxe", "suite"]:
        if known_type in value:
            return known_type

    return value


def otp_error_message(result: str, context: str) -> str:
    """
    Convert OTP result to guest-facing text.
    """

    if result == "invalid_format":
        return (
            "The verification code must "
            "contain exactly 6 digits."
        )

    if result == "expired":
        return (
            "That verification code has "
            "expired. Please request a new "
            f"{context} code."
        )

    if result == "too_many_attempts":
        return (
            "Too many incorrect verification "
            "attempts were made. Please request "
            "a new code."
        )

    if result == "not_found":
        return (
            "There is no active verification "
            f"code for this {context}. "
            "Please request a new code."
        )

    return (
        "That verification code is incorrect. "
        "Please check the code and try again."
    )



# RAG

@tool
def search_hotel_knowledge(query: str, hotel_id: int = 1) -> str:
    """
    Search hotel policies, amenities, menus,
    timings and frequently asked questions.
    """

    with SessionLocal() as db:
        rows = search_knowledge(db, query=query, hotel_id=hotel_id, limit=4)

    if not rows:
        return (
            "No matching hotel information "
            "was found. Do not guess; ask the "
            "guest to contact the front desk."
        )

    return "\n\n".join(
        (
            f"Source: {row.source}\n"
            f"{row.content}"
        )
        for row in rows
    )


# AVAILABILITY

@tool
def check_room_availability(room_type: str, check_in: str = "", check_out: str = "", hotel_id: int = 1) -> str:
    """
    Check room availability for the requested
    room type and stay dates.
    """

    (start, end, error) = parse_stay_dates(check_in, check_out)

    if error:
        return error

    room_type = (normalize_room_type(room_type))

    with SessionLocal() as db:
        rooms = find_available_rooms(db, hotel_id, room_type, start, end)

    if not rooms:
        return (
            f"No {room_type} rooms are "
            f"available from "
            f"{start.isoformat()} "
            f"to {end.isoformat()}."
        )

    cheapest = min(
        float(room.price_per_night)
        for room in rooms
    )

    return (
        f"{len(rooms)} {room_type} "
        f"room(s) are available from "
        f"{start.isoformat()} to "
        f"{end.isoformat()}. "
        f"Rates start at ₹{cheapest:.0f} "
        f"per night."
    )



# CREATE BOOKING

@tool
def create_booking(
    guest_name: str,
    guest_email: str,
    room_type: str,
    check_in: str = "",
    check_out: str = "",
    hotel_id: int = 1,
    otp: str = "",
) -> str:
    """
    Securely create a hotel booking using
    email OTP verification.
    """

    (start, end, error) = parse_stay_dates(check_in, check_out)


    if error:
        return error

    guest_name = (guest_name.strip())
    guest_email = (guest_email.strip().lower())

    room_type = (normalize_room_type(room_type))

    if not guest_name:
        return (
            "Guest name is required before "
            "creating a booking."
        )

    if not guest_email or "@" not in guest_email:
        return (
            "A valid guest email address "
            "is required before creating "
            "a booking."
        )

    request_hash = (
        build_booking_request_hash(
            hotel_id=hotel_id,
            guest_name=guest_name,
            guest_email=guest_email,
            room_type=room_type,
            check_in=start,
            check_out=end,
        )
    )

    if not otp.strip():

        with SessionLocal() as db:

            rooms = find_available_rooms(db, hotel_id, room_type, start, end)

            if not rooms:
                return (
                    f"No {room_type} rooms are "
                    f"currently available from "
                    f"{start.isoformat()} to "
                    f"{end.isoformat()}. "
                    "The booking was not created."
                )

            (generated_otp, result) = create_email_otp(db, email=guest_email, purpose="create_booking", request_hash=request_hash)

            if result == "cooldown":
                return (
                    "A booking verification code "
                    "was already sent recently. "
                    "Please check your email or "
                    "wait about one minute before "
                    "requesting another code."
                )

            if result != "created" or not generated_otp:
                return (
                    "I could not start booking "
                    "verification. Please try again."
                )

        email_sent = send_booking_creation_otp(guest_email= guest_email, otp=generated_otp, room_type=room_type, check_in=start, check_out=end)

        if not email_sent:

            with SessionLocal() as db:
                invalidate_latest_email_otp(db, guest_email, "create_booking",)

            return (
                "I could not send the booking "
                "verification code right now. "
                "The booking has not been created."
            )

        return (
            f"A 6-digit verification code "
            f"has been sent to {guest_email}. "
            f"Please enter the verification code "
            f"to confirm your {room_type} room "
            f"booking from {start.isoformat()} "
            f"to {end.isoformat()}. "
            "The booking has not been created yet."
        )

    with SessionLocal() as db:

        verified, result = (verify_email_otp(db, email=guest_email, purpose="create_booking", request_hash=request_hash, otp=otp))

        if not verified:
            return otp_error_message(result, "booking",)

        booking = create_booking_service(db, hotel_id=hotel_id, guest_name=guest_name, guest_email=guest_email, room_type=room_type, check_in=start, check_out=end)

        if not booking:
            return (
                "Your email was verified, "
                "but the room is no longer "
                "available for those dates."
            )

        room = db.get(Room, booking.room_id)

        if not room:
            return (
                "The booking was created, but "
                "the room information could "
                "not be found."
            )

        booking_id = booking.id
        room_number = room.number
        booked_room_type = room.room_type
        booked_check_in = booking.check_in
        booked_check_out = booking.check_out
        total = float(booking.total_amount)

    confirmation_sent = (
        send_booking_confirmation(
            guest_email=guest_email,
            guest_name=guest_name,
            booking_id=booking_id,
            room_number=room_number,
            room_type=booked_room_type,
            check_in=booked_check_in,
            check_out=booked_check_out,
            total_amount=total,
        )
    )

    if confirmation_sent:
        return (
            f"Booking confirmed. "
            f"Booking ID: {booking_id}. "
            f"Total amount: ₹{total:.0f}. "
            f"A confirmation email has been "
            f"sent to {guest_email}."
        )

    return (
        f"Booking confirmed. "
        f"Booking ID: {booking_id}. "
        f"Total amount: ₹{total:.0f}. "
        "The booking was created successfully, "
        "but the confirmation email could not "
        "be sent."
    )


# CANCEL BOOKING

@tool
def cancel_booking(booking_id: int, guest_email: str, otp: str = "") -> str:
    """
    Securely cancel an active booking
    using email OTP verification.
    """

    guest_email = guest_email.strip().lower()

    if not otp.strip():

        with SessionLocal() as db:

            (generated_otp, verified_email, result) = create_booking_otp(db, booking_id=booking_id, guest_email=guest_email, purpose="cancel")

            if result in {"not_found", "inactive"}:
                return (
                    "I could not verify an "
                    "active booking matching "
                    "those details."
                )

            if result == "cooldown":
                return (
                    "A verification code was "
                    "already sent recently. "
                    "Please check your email."
                )

            if result != "created" or not generated_otp or not verified_email:
                return (
                    "I could not start booking "
                    "verification."
                )

        email_sent = send_booking_verification_otp(verified_email, generated_otp, "cancel")
        

        if not email_sent:

            with SessionLocal() as db:
                invalidate_latest_otp(db, booking_id,"cancel")

            return (
                "I could not send the "
                "verification code."
            )

        return (
            f"A 6-digit verification code "
            f"has been sent to the email "
            f"associated with booking "
            f"#{booking_id}. Please enter "
            "the verification code to continue "
            "with the cancellation."
        )

    with SessionLocal() as db:

        verified, result = verify_booking_otp(db, booking_id=booking_id, purpose="cancel", otp=otp)

        if not verified:
            return otp_error_message(result, "cancellation")

        cancelled = cancel_booking_service(db, booking_id=booking_id, guest_email=guest_email)

    if not cancelled:
        return (
            "The verification succeeded, but "
            "the booking could not be cancelled."
        )

    return (
        f"Booking {booking_id} has been "
        f"cancelled successfully."
    )



# EXTEND BOOKING

@tool
def extend_booking(booking_id: int, guest_email: str, new_check_out: str, otp: str = "") -> str:
    """
    Securely extend an active hotel booking
    using email OTP verification.
    """

    guest_email = guest_email.strip().lower()

    try:
        new_date = parse_date_value(new_check_out)

    except ValueError:
        return (
            "Invalid date. Use YYYY-MM-DD, "
            "today, or tomorrow."
        )

    if new_date <= hotel_today():
        return (
            "The new checkout date must "
            "be a future date."
        )

    if not otp.strip():

        with SessionLocal() as db:

            (generated_otp, verified_email, result) = create_booking_otp(db, booking_id=booking_id, guest_email=guest_email, purpose="cancel")

            if result in {"not_found","inactive"}:
                return (
                    "I could not verify an "
                    "active booking matching "
                    "those details."
                )

            if result == "cooldown":
                return (
                    "A verification code was "
                    "already sent recently."
                )

            if result != "created" or not generated_otp or not verified_email:
                return (
                    "I could not start "
                    "booking verification."
                )

        email_sent = send_booking_verification_otp(verified_email, generated_otp, "extend")

        if not email_sent:

            with SessionLocal() as db:
                invalidate_latest_otp(db, booking_id, "extend",)

            return (
                "I could not send the "
                "verification code."
            )

        return (
            f"A 6-digit verification code "
            f"has been sent to the email "
            f"associated with booking "
            f"#{booking_id}. Please enter "
            "the verification code to continue "
            "with the extension."
        )

    with SessionLocal() as db:

        verified, result = verify_booking_otp(db, booking_id=booking_id, purpose="extend", otp=otp)

        if not verified:
            return otp_error_message(result, "extension")

        booking, result = extend_booking_service(db, booking_id=booking_id, guest_email=guest_email, new_check_out=new_date)
        

    if result == "not_found":
        return (
            "I could not find a booking "
            "matching those details."
        )

    if result == "inactive":
        return (
            "That booking is no longer active."
        )

    if result == "invalid_date":
        return (
            "The new checkout date must be "
            "later than the current checkout date."
        )

    if result == "unavailable":
        return (
            "The room is not available for "
            "the entire extension period."
        )

    if result == "room_not_found":
        return (
            "The room associated with this "
            "booking could not be found."
        )

    if not booking:
        return (
            "The booking could not be extended."
        )

    return (
        f"Booking {booking.id} has been "
        f"extended until {booking.check_out}. "
        f"The updated total is "
        f"₹{float(booking.total_amount):.0f}."
    )



# SERVICE REQUEST

@tool
def create_service_request(
    request_type: str,
    description: str,
    booking_id: int = 0,
    guest_email: str = "",
    room_number: str = "",
    hotel_id: int = 1,
    otp: str = "",
) -> str:
    """
    Securely create housekeeping, maintenance,
    room-service or other hotel service requests
    using booking verification and email OTP.
    """

    normalized_type = request_type.strip().lower().replace("-", "_").replace(" ", "_")

    try:
        kind = RequestType(normalized_type)

    except ValueError:

        allowed = ", ".join(
            item.value
            for item in RequestType
        )

        return (
            f"Unknown request type. "
            f"Use one of: {allowed}."
        )

    description = description.strip()

    guest_email = guest_email.strip().lower()

    room_number = room_number.strip()

    if not description:
        return (
            "Please describe what service "
            "you need."
        )

    if not booking_id:
        return (
            "Your booking ID is required "
            "to verify this service request."
        )

    if not guest_email or "@" not in guest_email:
        return (
            "The email address associated "
            "with the booking is required."
        )

    with SessionLocal() as db:

        booking, guest, room, booking_result = get_service_request_booking(db, hotel_id=hotel_id, booking_id=booking_id, guest_email=guest_email, room_number=room_number or None)

        if booking_result == "not_found":
            return (
                "I could not verify a booking "
                "matching that booking ID, "
                "email and room."
            )

        if booking_result == "inactive":
            return (
                "That booking is no longer active."
            )

        if booking_result == "not_current_stay":
            return (
                "Service requests can only "
                "be created during the active "
                "stay dates for that booking."
            )

        if not booking or not guest or not room:
            return (
                "I could not verify this stay."
            )

        verified_email = guest.email

        verified_room_number = room.number

        request_hash = build_service_request_hash(
                hotel_id=hotel_id,
                booking_id=booking.id,
                guest_email=verified_email,
                room_number=verified_room_number,
                request_type=kind.value,
                description=description,
            )

        if not otp.strip():

            generated_otp, result = create_email_otp(db, email=verified_email, purpose="service_request", request_hash=request_hash,)

            if result == "cooldown":
                return (
                    "A service-request verification "
                    "code was already sent recently."
                )

            if result != "created" or not generated_otp:
                return (
                    "I could not start "
                    "service-request verification."
                )

        else:
            generated_otp = None


    # SEND GUEST OTP

    if not otp.strip():

        email_sent = (
            send_service_request_otp(
                guest_email=verified_email,
                otp=generated_otp,
                request_type=kind.value,
                room_number=verified_room_number,
                description=description
            )
        )

        if not email_sent:

            with SessionLocal() as db:
                invalidate_latest_email_otp(db, verified_email, "service_request")

            return (
                "I could not send the "
                "service-request verification "
                "code. The request has not "
                "been created."
            )

        return (
            f"A 6-digit verification code "
            f"has been sent to the email "
            f"associated with booking "
            f"#{booking_id}. Please enter "
            f"the verification code to submit "
            f"the {kind.value} request for "
            f"room {verified_room_number}. "
            "The service request has not "
            "been created yet."
        )


    # VERIFY SERVICE OTP

    with SessionLocal() as db:

        (booking, guest, room, booking_result) = get_service_request_booking(db,hotel_id=hotel_id,booking_id=booking_id,guest_email=guest_email,room_number=room_number or None)

        if booking_result != "verified":
            return (
                "This stay is no longer eligible "
                "for a service request."
            )

        verified_email = guest.email

        verified_room_number = room.number

        request_hash = (
            build_service_request_hash(
                hotel_id=hotel_id,
                booking_id=booking.id,
                guest_email=verified_email,
                room_number=verified_room_number,
                request_type=kind.value,
                description=description,
            )
        )

        verified, result = verify_email_otp(db,email=verified_email, purpose="service_request", request_hash=request_hash, otp=otp)
        

        if not verified:
            return otp_error_message(result, "service request")

        (item, create_result,) = (
            create_service_request_service(
                db,
                hotel_id=hotel_id,
                booking_id=booking_id,
                guest_email=verified_email,
                request_type=kind,
                description=description,
                room_number=verified_room_number,
            )
        )

        if create_result != "created" or not item:
            return (
                "Your email was verified, but "
                "the service request could not "
                "be created."
            )

        request_id = item.id


    # DEPARTMENT EMAIL

    staff_notified = (
        send_service_request_staff_notification(
            request_id=request_id,
            booking_id=booking_id,
            request_type=kind.value,
            room_number=verified_room_number,
            description=description,
        )
    )

    department = get_department_name(kind.value)

    if staff_notified:
        return (
            f"Service request #{request_id} "
            f"was created for room "
            f"{verified_room_number} and "
            f"sent to the hotel staff. "
            f"The {department} team was "
            f"also notified by email."
        )

    return (
        f"Service request #{request_id} "
        f"was created for room "
        f"{verified_room_number} and "
        f"sent to the hotel staff dashboard. "
        "The staff notification email could "
        "not be sent, but the request remains "
        "active in the dashboard."
    )


HOTEL_TOOLS = [
    search_hotel_knowledge,
    check_room_availability,
    create_booking,
    cancel_booking,
    extend_booking,
    create_service_request,
]