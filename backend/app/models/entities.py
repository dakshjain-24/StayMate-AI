from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RoomStatus(str, Enum):
    available = "available"
    occupied = "occupied"
    cleaning = "cleaning"
    maintenance = "maintenance"


class BookingStatus(str, Enum):
    confirmed = "confirmed"
    checked_in = "checked_in"
    checked_out = "checked_out"
    cancelled = "cancelled"


class RequestType(str, Enum):
    housekeeping = "housekeeping"
    maintenance = "maintenance"
    room_service = "room_service"
    other = "other"


class RequestStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class Hotel(Base):
    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    city: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    rooms: Mapped[list["Room"]] = relationship(
        back_populates="hotel",
        cascade="all, delete-orphan",
    )


class StaffUser(Base):
    __tablename__ = "staff_users"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    hotel_id: Mapped[int] = mapped_column(
        ForeignKey(
            "hotels.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(180),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Guest(Base):
    __tablename__ = "guests"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(180),
        unique=True,
        nullable=False,
        index=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(30)
    )

    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="guest"
    )


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    hotel_id: Mapped[int] = mapped_column(
        ForeignKey(
            "hotels.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    room_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    price_per_night: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    status: Mapped[RoomStatus] = mapped_column(
        SqlEnum(RoomStatus),
        default=RoomStatus.available,
    )

    hotel: Mapped["Hotel"] = relationship(
        back_populates="rooms"
    )

    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="room"
    )


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    hotel_id: Mapped[int] = mapped_column(
        ForeignKey("hotels.id"),
        index=True,
    )

    guest_id: Mapped[int] = mapped_column(
        ForeignKey("guests.id"),
        index=True,
    )

    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id"),
        index=True,
    )

    check_in: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    check_out: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    status: Mapped[BookingStatus] = mapped_column(
        SqlEnum(BookingStatus),
        default=BookingStatus.confirmed,
    )

    total_amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    guest: Mapped["Guest"] = relationship(
        back_populates="bookings"
    )

    room: Mapped["Room"] = relationship(
        back_populates="bookings"
    )


class BookingVerification(Base):
    """
    OTP verification for an existing booking.

    Used for:
    - cancellation
    - extension
    """

    __tablename__ = "booking_verifications"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    booking_id: Mapped[int] = mapped_column(
        ForeignKey(
            "bookings.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    purpose: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    otp_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class EmailVerification(Base):
    """
    OTP verification before a booking exists.

    The request_hash binds the OTP to the exact
    reservation details the guest approved.
    """

    __tablename__ = "email_verifications"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    email: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
        index=True,
    )

    purpose: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    request_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    otp_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    hotel_id: Mapped[int] = mapped_column(
        ForeignKey("hotels.id"),
        index=True,
    )

    room_id: Mapped[int | None] = mapped_column(
        ForeignKey("rooms.id"),
        nullable=True,
        index=True,
    )

    guest_id: Mapped[int | None] = mapped_column(
        ForeignKey("guests.id"),
        nullable=True,
        index=True,
    )

    request_type: Mapped[RequestType] = mapped_column(
        SqlEnum(RequestType),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[RequestStatus] = mapped_column(
        SqlEnum(RequestStatus),
        default=RequestStatus.open,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    hotel_id: Mapped[int] = mapped_column(
        ForeignKey("hotels.id"),
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    embedding: Mapped[list[float]] = mapped_column(
        Vector(1536),
        nullable=False,
    )