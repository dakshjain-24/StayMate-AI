from html import escape

import resend

from app.core.config import settings



# BASE EMAIL SENDER

def _send_email(to: str, subject: str, html: str) -> bool:
    """
    Send an email through Resend.
    """

    if not settings.resend_api_key:
        print("RESEND_API_KEY is not configured.")
        return False

    if not to:
        print("Email recipient is not configured.")
        return False

    resend.api_key = settings.resend_api_key

    try:
        resend.Emails.send(
            {
                "from": settings.email_from,
                "to": [to],
                "subject": subject,
                "html": html
            }
        )

        return True

    except Exception as exc:
        print(f"Email sending failed: {exc}")
        return False



# BOOKING CONFIRMATION

def send_booking_confirmation(
    guest_email: str,
    guest_name: str,
    booking_id: int,
    room_number: str,
    room_type: str,
    check_in,
    check_out,
    total_amount: float,
) -> bool:
    """
    Send booking confirmation to the guest.
    """

    return _send_email(
        guest_email,
        f"Booking Confirmed - StayMate #{booking_id}",
        f"""
        <div
            style="
                font-family: Arial, sans-serif;
                max-width: 520px;
                margin: auto;
            "
        >

            <h2>
                Booking Confirmed
            </h2>

            <p>
                Hi {escape(guest_name)},
            </p>

            <p>
                Your StayMate reservation
                has been confirmed.
            </p>

            <p>
                <strong>Booking ID:</strong>
                #{booking_id}
                <br>

                <strong>Room:</strong>
                {escape(str(room_number))}
                <br>

                <strong>Room Type:</strong>
                {escape(str(room_type))}
                <br>

                <strong>Check-in:</strong>
                {check_in}
                <br>

                <strong>Check-out:</strong>
                {check_out}
                <br>

                <strong>Total:</strong>
                ₹{total_amount:.0f}
            </p>

            <p>
                We look forward to hosting you.
            </p>

        </div>
        """,
    )



# BOOKING CREATION OTP

def send_booking_creation_otp(guest_email: str, otp: str, room_type: str, check_in, check_out) -> bool:
    """
    Send OTP before creating a new booking.
    """

    return _send_email(
        guest_email,
        "StayMate Booking Verification",
        f"""
        <div
            style="
                font-family: Arial, sans-serif;
                max-width: 500px;
                margin: auto;
            "
        >

            <h2>
                Confirm Your StayMate Booking
            </h2>

            <p>
                We received a request to book:
            </p>

            <p>
                <strong>Room Type:</strong>
                {escape(str(room_type))}
                <br>

                <strong>Check-in:</strong>
                {check_in}
                <br>

                <strong>Check-out:</strong>
                {check_out}
            </p>

            <p>
                Enter this verification code
                in StayMate:
            </p>

            <div
                style="
                    font-size: 32px;
                    font-weight: bold;
                    letter-spacing: 8px;
                    padding: 16px 0;
                "
            >
                {otp}
            </div>

            <p>
                This code expires in
                <strong>5 minutes</strong>.
            </p>

            <p>
                The booking will not be created
                until this code is verified.
            </p>

            <p
                style="
                    color: #777;
                    font-size: 13px;
                "
            >
                If you did not request this
                reservation, ignore this email.
            </p>

        </div>
        """,
    )



# CANCEL / EXTEND OTP

def send_booking_verification_otp(guest_email: str, otp: str, purpose: str) -> bool:
    """
    Send OTP for cancellation or extension.
    """

    if purpose == "cancel":
        action_text = ("cancel your reservation")
        subject = ("StayMate Cancellation Verification")

    else:
        action_text = ("extend your reservation")
        subject = ("StayMate Stay Extension Verification")

    return _send_email(
        guest_email,
        subject,

        f"""
        <div
            style="
                font-family: Arial, sans-serif;
                max-width: 500px;
                margin: auto;
            "
        >

            <h2>
                StayMate Verification
            </h2>

            <p>
                We received a request to
                <strong>
                    {action_text}
                </strong>.
            </p>

            <p>
                Enter the following code
                in StayMate:
            </p>

            <div
                style="
                    font-size: 32px;
                    font-weight: bold;
                    letter-spacing: 8px;
                    padding: 16px 0;
                "
            >
                {otp}
            </div>

            <p>
                This code expires in
                <strong>5 minutes</strong>.
            </p>

            <p>
                This code can only be used once.
            </p>

        </div>
        """,
    )



# SERVICE REQUEST OTP

def send_service_request_otp(guest_email: str, otp: str, request_type: str, room_number: str, description: str) -> bool:
    """
    Send OTP before creating a service request.
    """

    return _send_email(
        guest_email,
        "StayMate Service Request Verification",
        f"""
        <div
            style="
                font-family: Arial, sans-serif;
                max-width: 500px;
                margin: auto;
            "
        >

            <h2>
                Verify Your Service Request
            </h2>

            <p>
                We received the following request:
            </p>

            <p>
                <strong>Type:</strong>
                {escape(str(request_type))}
                <br>

                <strong>Room:</strong>
                {escape(str(room_number))}
                <br>

                <strong>Request:</strong>
                {escape(description)}
            </p>

            <p>
                Enter this verification code
                in StayMate:
            </p>

            <div
                style="
                    font-size: 32px;
                    font-weight: bold;
                    letter-spacing: 8px;
                    padding: 16px 0;
                "
            >
                {otp}
            </div>

            <p>
                This code expires in
                <strong>5 minutes</strong>.
            </p>

            <p>
                The service request will not be
                created until this code is verified.
            </p>

        </div>
        """,
    )



# DEPARTMENT HELPERS

def normalize_request_type(request_type: str) -> str:
    """
    Convert request type into a consistent format.
    """

    return request_type.strip().lower().replace("-", "_").replace(" ", "_")


def get_department_name(request_type: str) -> str:
    """
    Return human-readable department name.
    """

    normalized = normalize_request_type(request_type)


    names = {
        "housekeeping": "Housekeeping",
        "maintenance": "Maintenance",
        "room_service": "Room Service",
    }

    return names.get(normalized, "Front Desk")


def get_department_email(request_type: str,) -> str | None:
    """
    Return department notification email
    from application settings.
    """

    normalized = normalize_request_type(request_type)


    department_emails = {
        "housekeeping": settings.housekeeping_email,
        "maintenance": settings.maintenance_email,
        "room_service": settings.room_service_email
    }

    recipient = department_emails.get(normalized)


    if not recipient:
        recipient = settings.front_desk_email


    if not recipient:
        return None

    return recipient.strip()



# STAFF SERVICE REQUEST NOTIFICATION

def send_service_request_staff_notification(request_id: int, booking_id: int, request_type: str, room_number: str, description: str) -> bool:
    """
    Notify the appropriate hotel department after a verified service request is created.
    Failure to send this email does not remove or rollback the service request.
    """

    recipient = get_department_email(request_type)
    

    if not recipient:
        print(f"No department email configured for request type: {request_type}")

        return False

    department = get_department_name(request_type)
    

    safe_department = escape(department)

    safe_room = escape(str(room_number))

    safe_description = escape(description)

    subject = (
        f"[StayMate] New {department} "
        f"Request #{request_id} - "
        f"Room {room_number}"
    )

    email_sent = _send_email(
        recipient,
        subject,
        f"""
        <div
            style="
                font-family: Arial, sans-serif;
                max-width: 560px;
                margin: auto;
                line-height: 1.5;
            "
        >

            <h2>
                New {safe_department} Request
            </h2>

            <p>
                A guest service request has
                been verified and submitted.
            </p>

            <div
                style="
                    background: #f6f7f9;
                    border-radius: 10px;
                    padding: 18px;
                    margin: 18px 0;
                "
            >

                <p>
                    <strong>Request ID:</strong>
                    #{request_id}
                </p>

                <p>
                    <strong>Booking ID:</strong>
                    #{booking_id}
                </p>

                <p>
                    <strong>Room:</strong>
                    {safe_room}
                </p>

                <p>
                    <strong>Department:</strong>
                    {safe_department}
                </p>

                <p>
                    <strong>Status:</strong>
                    Open
                </p>

                <p>
                    <strong>Guest Request:</strong>
                    <br>
                    {safe_description}
                </p>

            </div>

            <p>
                Please open the StayMate Staff Dashboard
                to start or complete this request.
            </p>

            <p
                style="
                    color: #777;
                    font-size: 13px;
                "
            >
                This notification was generated
                automatically by StayMate.
            </p>

        </div>
        """,
    )

    if email_sent:
        print(f"Department notification sent to {recipient}")

    return email_sent