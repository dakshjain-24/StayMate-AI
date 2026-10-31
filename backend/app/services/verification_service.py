import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    Booking,
    BookingStatus,
    BookingVerification,
    EmailVerification,
    Guest,
)


OTP_EXPIRY_MINUTES = 5
OTP_RESEND_COOLDOWN_SECONDS = 60
MAX_OTP_ATTEMPTS = 5


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def generate_otp() -> str:
    return str(secrets.randbelow(900000) + 100000)


def validate_otp_format(otp: str) -> bool:
    otp = otp.strip()

    return (
        otp.isdigit()
        and len(otp) == 6
    )


# EXISTING BOOKING OTP
# Cancellation / Extension

def hash_booking_otp(booking_id: int, purpose: str, otp: str) -> str:

    if not settings.otp_secret:
        raise RuntimeError(
            "OTP_SECRET is not configured."
        )

    message = (
        f"{booking_id}:"
        f"{purpose}:"
        f"{otp}"
    )

    return hmac.new(settings.otp_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256,).hexdigest()


def get_matching_booking(db: Session, booking_id: int, guest_email: str) -> tuple[Booking | None, Guest | None]:

    row = db.execute(
        select(
            Booking,
            Guest,
        )
        .join(
            Guest,
            Booking.guest_id == Guest.id,
        )
        .where(
            Booking.id == booking_id,
            func.lower(Guest.email) == guest_email.strip().lower(),
        )
    ).first()

    if not row:
        return (None, None)

    booking, guest = row

    return (booking, guest)


def create_booking_otp(
    db: Session,
    booking_id: int,
    guest_email: str,
    purpose: str,
) -> tuple[
    str | None,
    str | None,
    str,
]:

    if purpose not in {
        "cancel",
        "extend",
    }:
        return (
            None,
            None,
            "invalid_purpose",
        )

    booking, guest = (
        get_matching_booking(
            db,
            booking_id,
            guest_email,
        )
    )

    if (
        not booking
        or not guest
    ):
        return (
            None,
            None,
            "not_found",
        )

    if booking.status not in [
        BookingStatus.confirmed,
        BookingStatus.checked_in,
    ]:
        return (
            None,
            None,
            "inactive",
        )

    latest = db.scalar(
        select(
            BookingVerification
        )
        .where(
            BookingVerification.booking_id
            == booking_id,

            BookingVerification.purpose
            == purpose,

            BookingVerification.used
            == False,
        )
        .order_by(
            BookingVerification
            .created_at
            .desc()
        )
    )

    if latest and latest.created_at:

        seconds_since_last_code = (
            utc_now()
            - ensure_aware(
                latest.created_at
            )
        ).total_seconds()

        if (
            seconds_since_last_code
            <
            OTP_RESEND_COOLDOWN_SECONDS
        ):
            return (
                None,
                guest.email,
                "cooldown",
            )

    old_codes = list(
        db.scalars(
            select(
                BookingVerification
            )
            .where(
                BookingVerification.booking_id
                == booking_id,

                BookingVerification.purpose
                == purpose,

                BookingVerification.used
                == False,
            )
        ).all()
    )

    for item in old_codes:
        item.used = True

    otp = generate_otp()

    verification = BookingVerification(
        booking_id=booking_id,
        purpose=purpose,
        otp_hash=hash_booking_otp(
            booking_id,
            purpose,
            otp,
        ),
        expires_at=(
            utc_now()
            + timedelta(
                minutes=
                OTP_EXPIRY_MINUTES
            )
        ),
        attempts=0,
        used=False,
    )

    db.add(
        verification
    )

    db.commit()

    return (
        otp,
        guest.email,
        "created",
    )


def invalidate_latest_otp(
    db: Session,
    booking_id: int,
    purpose: str,
) -> None:

    verification = db.scalar(
        select(
            BookingVerification
        )
        .where(
            BookingVerification.booking_id
            == booking_id,

            BookingVerification.purpose
            == purpose,

            BookingVerification.used
            == False,
        )
        .order_by(
            BookingVerification
            .created_at
            .desc()
        )
    )

    if verification:
        verification.used = True
        db.commit()


def verify_booking_otp(
    db: Session,
    booking_id: int,
    purpose: str,
    otp: str,
) -> tuple[
    bool,
    str,
]:

    otp = otp.strip()

    if not validate_otp_format(
        otp
    ):
        return (
            False,
            "invalid_format",
        )

    verification = db.scalar(
        select(
            BookingVerification
        )
        .where(
            BookingVerification.booking_id
            == booking_id,

            BookingVerification.purpose
            == purpose,

            BookingVerification.used
            == False,
        )
        .order_by(
            BookingVerification
            .created_at
            .desc()
        )
    )

    if not verification:
        return (
            False,
            "not_found",
        )

    if (
        utc_now()
        >
        ensure_aware(
            verification.expires_at
        )
    ):
        verification.used = True

        db.commit()

        return (
            False,
            "expired",
        )

    if (
        verification.attempts
        >= MAX_OTP_ATTEMPTS
    ):
        verification.used = True

        db.commit()

        return (
            False,
            "too_many_attempts",
        )

    expected_hash = (
        hash_booking_otp(
            booking_id,
            purpose,
            otp,
        )
    )

    if not hmac.compare_digest(
        verification.otp_hash,
        expected_hash,
    ):

        verification.attempts += 1

        if (
            verification.attempts
            >= MAX_OTP_ATTEMPTS
        ):
            verification.used = True

        db.commit()

        return (
            False,
            "invalid",
        )

    verification.used = True

    db.commit()

    return (
        True,
        "verified",
    )


# =========================================================
# EMAIL OTP
# Booking Creation / Service Requests
# =========================================================

def build_booking_request_hash(
    hotel_id: int,
    guest_name: str,
    guest_email: str,
    room_type: str,
    check_in,
    check_out,
) -> str:

    canonical = (
        f"{hotel_id}|"
        f"{guest_name.strip().lower()}|"
        f"{guest_email.strip().lower()}|"
        f"{room_type.strip().lower()}|"
        f"{check_in.isoformat()}|"
        f"{check_out.isoformat()}"
    )

    return hashlib.sha256(
        canonical.encode(
            "utf-8"
        )
    ).hexdigest()


def build_service_request_hash(
    hotel_id: int,
    booking_id: int,
    guest_email: str,
    room_number: str,
    request_type: str,
    description: str,
) -> str:
    """
    Bind the OTP to the exact service request.

    This means an OTP requested for towels
    cannot later be reused for a different
    maintenance request.
    """

    canonical = (
        f"{hotel_id}|"
        f"{booking_id}|"
        f"{guest_email.strip().lower()}|"
        f"{room_number.strip().lower()}|"
        f"{request_type.strip().lower()}|"
        f"{description.strip().lower()}"
    )

    return hashlib.sha256(
        canonical.encode(
            "utf-8"
        )
    ).hexdigest()


def hash_email_otp(
    email: str,
    purpose: str,
    request_hash: str,
    otp: str,
) -> str:

    if not settings.otp_secret:
        raise RuntimeError(
            "OTP_SECRET is not configured."
        )

    message = (
        f"{email.strip().lower()}:"
        f"{purpose}:"
        f"{request_hash}:"
        f"{otp}"
    )

    return hmac.new(
        settings.otp_secret.encode(
            "utf-8"
        ),
        message.encode(
            "utf-8"
        ),
        hashlib.sha256,
    ).hexdigest()


def create_email_otp(
    db: Session,
    email: str,
    purpose: str,
    request_hash: str,
) -> tuple[
    str | None,
    str,
]:

    email = (
        email
        .strip()
        .lower()
    )

    if purpose not in {
        "create_booking",
        "service_request",
    }:
        return (
            None,
            "invalid_purpose",
        )

    latest = db.scalar(
        select(
            EmailVerification
        )
        .where(
            func.lower(
                EmailVerification.email
            )
            == email,

            EmailVerification.purpose
            == purpose,

            EmailVerification.used
            == False,
        )
        .order_by(
            EmailVerification
            .created_at
            .desc()
        )
    )

    if latest and latest.created_at:

        seconds_since_last_code = (
            utc_now()
            - ensure_aware(
                latest.created_at
            )
        ).total_seconds()

        if (
            seconds_since_last_code
            <
            OTP_RESEND_COOLDOWN_SECONDS
        ):
            return (
                None,
                "cooldown",
            )

    previous_codes = list(
        db.scalars(
            select(
                EmailVerification
            )
            .where(
                func.lower(
                    EmailVerification.email
                )
                == email,

                EmailVerification.purpose
                == purpose,

                EmailVerification.used
                == False,
            )
        ).all()
    )

    for item in previous_codes:
        item.used = True

    otp = generate_otp()

    verification = EmailVerification(
        email=email,
        purpose=purpose,
        request_hash=
            request_hash,
        otp_hash=
            hash_email_otp(
                email,
                purpose,
                request_hash,
                otp,
            ),
        expires_at=(
            utc_now()
            + timedelta(
                minutes=
                OTP_EXPIRY_MINUTES
            )
        ),
        attempts=0,
        used=False,
    )

    db.add(
        verification
    )

    db.commit()

    return (
        otp,
        "created",
    )


def invalidate_latest_email_otp(
    db: Session,
    email: str,
    purpose: str,
) -> None:

    verification = db.scalar(
        select(
            EmailVerification
        )
        .where(
            func.lower(
                EmailVerification.email
            )
            == email
            .strip()
            .lower(),

            EmailVerification.purpose
            == purpose,

            EmailVerification.used
            == False,
        )
        .order_by(
            EmailVerification
            .created_at
            .desc()
        )
    )

    if verification:
        verification.used = True
        db.commit()


def verify_email_otp(
    db: Session,
    email: str,
    purpose: str,
    request_hash: str,
    otp: str,
) -> tuple[
    bool,
    str,
]:

    email = (
        email
        .strip()
        .lower()
    )

    otp = otp.strip()

    if not validate_otp_format(
        otp
    ):
        return (
            False,
            "invalid_format",
        )

    verification = db.scalar(
        select(
            EmailVerification
        )
        .where(
            func.lower(
                EmailVerification.email
            )
            == email,

            EmailVerification.purpose
            == purpose,

            EmailVerification.request_hash
            == request_hash,

            EmailVerification.used
            == False,
        )
        .order_by(
            EmailVerification
            .created_at
            .desc()
        )
    )

    if not verification:
        return (
            False,
            "not_found",
        )

    if (
        utc_now()
        >
        ensure_aware(
            verification.expires_at
        )
    ):
        verification.used = True

        db.commit()

        return (
            False,
            "expired",
        )

    if (
        verification.attempts
        >= MAX_OTP_ATTEMPTS
    ):
        verification.used = True

        db.commit()

        return (
            False,
            "too_many_attempts",
        )

    expected_hash = (
        hash_email_otp(
            email,
            purpose,
            request_hash,
            otp,
        )
    )

    if not hmac.compare_digest(
        verification.otp_hash,
        expected_hash,
    ):

        verification.attempts += 1

        if (
            verification.attempts
            >= MAX_OTP_ATTEMPTS
        ):
            verification.used = True

        db.commit()

        return (
            False,
            "invalid",
        )

    verification.used = True

    db.commit()

    return (
        True,
        "verified",
    )