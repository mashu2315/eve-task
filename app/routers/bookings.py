import math
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from loguru import logger

from app.db import get_db
from app.models import Booking, BookingStatus, DiagnosticCentre, DiagnosticTest, User
from app.schemas import BookingCreate, BookingRead, PaginatedResponse
from app.security import get_current_user
from app.exceptions import DiagnosticAppException
from app.limiter import limiter

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.post("/", response_model=BookingRead, status_code=status.HTTP_201_CREATED, summary="Create a new Booking")
@limiter.limit("10/minute")
def create_booking(request: Request, payload: BookingCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == payload.centre_id).first()
    if not centre:
        raise DiagnosticAppException(f"Diagnostic centre with ID {payload.centre_id} not found.", status_code=404)

    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == payload.test_id).first()
    if not test:
        raise DiagnosticAppException(f"Diagnostic test with ID {payload.test_id} not found.", status_code=404)

    if test.centre_id != payload.centre_id:
        raise DiagnosticAppException(
            message="The selected test is not offered by the selected diagnostic centre.",
            status_code=400,
            resolution="Please ensure you are selecting a test that belongs to the chosen centre."
        )

    booking = Booking(
        user_id=current_user.id,
        test_id=test.id,
        centre_id=centre.id,
        appointment_datetime=payload.appointment_datetime,
        amount=test.price,
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    logger.info(f"Booking {booking.id} created for user {current_user.email}")
    return booking

@router.get("/", response_model=PaginatedResponse[BookingRead], summary="List User Bookings")
@limiter.limit("20/minute")
def list_bookings(request: Request, page: int = 1, size: int = 10, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if page < 1 or size < 1:
        raise DiagnosticAppException("Page and size must be strictly positive integers.")
        
    base_query = db.query(Booking).filter(Booking.user_id == current_user.id)
    total_items = base_query.count()
    total_pages = math.ceil(total_items / size) if size > 0 else 0
    bookings = base_query.order_by(Booking.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    return PaginatedResponse(
        items=bookings,
        page=page,
        size=size,
        total_pages=total_pages,
        total_items=total_items
    )

@router.get("/{booking_id}", response_model=BookingRead, summary="Get Booking Details")
@limiter.limit("20/minute")
def get_booking(request: Request, booking_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise DiagnosticAppException(f"Booking with ID {booking_id} not found.", status_code=404)
    if booking.user_id != current_user.id:
        raise DiagnosticAppException(
            message="You are not authorized to view this booking.",
            status_code=403,
            resolution="Ensure you are logged into the account that created the booking."
        )
    return booking

@router.patch("/{booking_id}/cancel", summary="Cancel a Booking")
@limiter.limit("5/minute")
def cancel_booking(request: Request, booking_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise DiagnosticAppException(f"Booking with ID {booking_id} not found.", status_code=404)
    if booking.user_id != current_user.id:
        raise DiagnosticAppException("You are not authorized to cancel this booking.", status_code=403)
        
    if booking.status in {BookingStatus.CANCELLED, BookingStatus.CONFIRMED}:
        raise DiagnosticAppException(
            message=f"Booking cannot be cancelled because its status is '{booking.status}'.",
            status_code=400,
            resolution="Only PENDING or FAILED bookings can be cancelled."
        )
        
    booking.status = BookingStatus.CANCELLED
    db.commit()
    logger.info(f"Booking {booking_id} was cancelled by user {current_user.email}")
    return {"message": "Booking cancelled successfully", "booking_id": booking.id}
