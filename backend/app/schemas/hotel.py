from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import BookingStatus, RequestStatus, RequestType, RoomStatus


class GuestCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None


class RoomOut(BaseModel):
    id: int
    number: str
    room_type: str
    price_per_night: float
    status: RoomStatus

    model_config = ConfigDict(from_attributes=True)



class ServiceRequestStatusUpdate(BaseModel):
    status: RequestStatus


class BookingCreate(BaseModel):
    guest_name: str
    guest_email: EmailStr
    room_type: str
    check_in: date
    check_out: date
    hotel_id: int = 1


class BookingOut(BaseModel):
    id: int
    guest_name: str
    guest_email: str
    room_number: str
    room_type: str
    check_in: date
    check_out: date
    status: BookingStatus
    total_amount: float


class ServiceRequestCreate(BaseModel):
    room_number: str | None = None
    guest_email: EmailStr | None = None
    request_type: RequestType
    description: str = Field(min_length=3, max_length=1000)
    hotel_id: int = 1


class ServiceRequestOut(BaseModel):
    id: int
    room_number: str | None
    guest_email: str | None
    request_type: RequestType
    description: str
    status: RequestStatus
    created_at: datetime


class DashboardStats(BaseModel):
    total_rooms: int
    available_rooms: int
    active_bookings: int
    open_service_requests: int
