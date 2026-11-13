import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models import Guest, Room, StaffUser
from app.schemas.auth import StaffIdentity, StaffLoginRequest, StaffLoginResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.hotel import (
    BookingOut,
    DashboardStats,
    RoomOut,
    ServiceRequestOut,
    ServiceRequestStatusUpdate,
)
from app.services.agent_service import chat_with_receptionist
from app.services.auth_service import authenticate_staff, create_access_token, get_current_staff
from app.services.hotel_service import get_dashboard_stats, list_bookings, list_service_requests, update_service_request_status



# LOGGER
logger = logging.getLogger(__name__)


# ROUTER
router = APIRouter(prefix="/api")


# PUBLIC
@router.get("/health")
def health():
    return {
        "status": "ok"
    }


# PUBLIC CHAT
# 30 requests / minute / IP
@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
def chat(request: Request, payload: ChatRequest):

    try:
        hotel_id = (settings.default_hotel_id)
        answer = chat_with_receptionist(payload.message, payload.thread_id, hotel_id)

    except Exception:

        logger.exception("Agent request failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Something went wrong while "
                "processing your request. "
                "Please try again."
            )
        )

    return ChatResponse(answer=answer, thread_id=payload.thread_id)


# STAFF AUTH
# 5 attempts / minute / IP

@router.post("/auth/login", response_model=StaffLoginResponse)
@limiter.limit("5/minute")
def staff_login(request: Request, payload: StaffLoginRequest, db: Session = Depends(get_db)):

    staff = authenticate_staff(db, email=str(payload.email), password=payload.password,)

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token(staff)

    return StaffLoginResponse(
        access_token=token,
        staff=StaffIdentity(
            id=staff.id,
            name=staff.name,
            email=staff.email,
            hotel_id=staff.hotel_id,
        )
    )



# CURRENT STAFF USER

@router.get("/auth/me", response_model=StaffIdentity)
def staff_me(staff: StaffUser = Depends(get_current_staff)):

    return StaffIdentity(
        id=staff.id,
        name=staff.name,
        email=staff.email,
        hotel_id=staff.hotel_id,
    )



# PROTECTED DASHBOARD

@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db), staff: StaffUser = Depends(get_current_staff)):

    return get_dashboard_stats(db, staff.hotel_id)



# PROTECTED ROOMS

@router.get("/rooms", response_model=list[RoomOut])
def rooms(db: Session = Depends(get_db), staff: StaffUser = Depends(get_current_staff)):

    stmt = select(Room).where(Room.hotel_id==staff.hotel_id).order_by(Room.number)
    return list(db.scalars(stmt).all())



# PROTECTED BOOKINGS

@router.get("/bookings", response_model=list[BookingOut])
def bookings(db: Session = Depends(get_db), staff: StaffUser = Depends(get_current_staff)):

    rows = list_bookings(db, staff.hotel_id,)

    return [
        BookingOut(
            id=row.id,
            guest_name=row.guest.name,
            guest_email=row.guest.email,
            room_number=row.room.number,
            room_type=row.room.room_type,
            check_in=row.check_in,
            check_out=row.check_out,
            status=row.status,
            total_amount=float(row.total_amount)
        )
        for row in rows
    ]



# PROTECTED SERVICE REQUESTS

@router.get("/service-requests", response_model=list[ServiceRequestOut])
def service_requests(db: Session = Depends(get_db), staff: StaffUser = Depends(get_current_staff)):

    rows = list_service_requests(db, staff.hotel_id,)
    result: list[ServiceRequestOut] = []

    for row in rows:
        room_number = None
        guest_email = None

        # ROOM
        if row.room_id:
            room = db.get(Room, row.room_id,)
            if room and room.hotel_id == staff.hotel_id:
                room_number = room.number

        # GUEST
        if row.guest_id:
            guest = db.get(Guest, row.guest_id)

            if guest:
                guest_email = guest.email

        # RESPONSE
        result.append(
            ServiceRequestOut(
                id=row.id,
                room_number=room_number,
                guest_email=guest_email,
                request_type=row.request_type,
                description=row.description,
                status=row.status,
                created_at=row.created_at
            )
        )

    return result


# PROTECTED STATUS UPDATE
@router.patch("/service-requests/{request_id}/status", response_model=ServiceRequestOut)
@limiter.limit("30/minute")
def update_request_status(
    request: Request,
    request_id: int,
    payload:ServiceRequestStatusUpdate,
    db: Session = Depends(get_db),
    staff: StaffUser = Depends(get_current_staff)
):


    # VERIFY OWNERSHIP
    rows = list_service_requests(db, staff.hotel_id)

    allowed_ids = {
        row.id
        for row in rows
    }

    if request_id not in allowed_ids:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found"
        )

    
    # UPDATE STATUS
    item = update_service_request_status(db, request_id, payload.status)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found"
        )


    # BUILD RESPONSE
    room_number = None
    guest_email = None

    if item.room_id:
        room = db.get(Room, item.room_id)

        if room and room.hotel_id == staff.hotel_id:
            room_number = room.number

    if item.guest_id:
        guest = db.get(Guest, item.guest_id)
        if guest:
            guest_email = guest.email

    return ServiceRequestOut(
        id=item.id,
        room_number=room_number,
        guest_email=guest_email,
        request_type=item.request_type,
        description=item.description,
        status=item.status,
        created_at=item.created_at
    )