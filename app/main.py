from datetime import datetime, timedelta
import math
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.db import Base, engine, get_db
from app.models import Booking, BookingStatus, DiagnosticCentre, DiagnosticTest, Payment, PaymentStatus, WebhookEvent
from app.schemas import (
    BookingCreate,
    BookingRead,
    DiagnosticCentreCreate,
    DiagnosticCentreRead,
    DiagnosticTestCreate,
    DiagnosticTestRead,
    PaymentCreate,
    PaymentRead,
    PaymentWebhookEvent,
    PaymentWebhookResponse,
    Token,
    PaginatedResponse,
    UserCreate,
    UserLogin,
)
from app.security import create_access_token, get_current_user, hash_password, verify_password
from app.models import User

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Diagnostic Booking Service", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

Base.metadata.create_all(bind=engine)


@app.get("/health")
@limiter.limit("10/minute")
def health_check(request: Request):
    return {"status": "ok"}


@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def signup(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    user = User(
        full_name=payload.full_name.strip(),
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User created successfully", "user_id": user.id}


@app.post("/auth/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/token", response_model=Token)
@limiter.limit("10/minute")
def login_form(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username.lower()).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/centres/", response_model=DiagnosticCentreRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_centre(request: Request, payload: DiagnosticCentreCreate, db: Session = Depends(get_db)):
    centre = DiagnosticCentre(name=payload.name.strip(), location=payload.location.strip(), phone=payload.phone)
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


@app.get("/centres/", response_model=PaginatedResponse[DiagnosticCentreRead])
@limiter.limit("20/minute")
def list_centres(request: Request, page: int = 1, size: int = 10, db: Session = Depends(get_db)):
    total_items = db.query(DiagnosticCentre).count()
    total_pages = math.ceil(total_items / size) if size > 0 else 0
    centres = db.query(DiagnosticCentre).offset((page - 1) * size).limit(size).all()
    return PaginatedResponse(
        items=centres,
        page=page,
        size=size,
        total_pages=total_pages,
        total_items=total_items
    )


@app.get("/centres/{centre_id}", response_model=DiagnosticCentreRead)
@limiter.limit("20/minute")
def get_centre(request: Request, centre_id: int, db: Session = Depends(get_db)):
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == centre_id).first()
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")
    return centre


@app.post("/centres/{centre_id}/tests/", response_model=DiagnosticTestRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_test_for_centre(request: Request, centre_id: int, payload: DiagnosticTestCreate, db: Session = Depends(get_db)):
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == centre_id).first()
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")

    test = DiagnosticTest(
        name=payload.name.strip(),
        description=payload.description,
        price=payload.price,
        centre_id=centre_id,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@app.get("/tests/", response_model=PaginatedResponse[DiagnosticTestRead])
@limiter.limit("20/minute")
def list_tests(request: Request, page: int = 1, size: int = 10, db: Session = Depends(get_db)):
    total_items = db.query(DiagnosticTest).count()
    total_pages = math.ceil(total_items / size) if size > 0 else 0
    tests = db.query(DiagnosticTest).offset((page - 1) * size).limit(size).all()
    return PaginatedResponse(
        items=tests,
        page=page,
        size=size,
        total_pages=total_pages,
        total_items=total_items
    )


@app.get("/tests/{test_id}", response_model=DiagnosticTestRead)
@limiter.limit("20/minute")
def get_test(request: Request, test_id: int, db: Session = Depends(get_db)):
    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Diagnostic test not found")
    return test


@app.post("/bookings/", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_booking(request: Request, payload: BookingCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == payload.centre_id).first()
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")

    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == payload.test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Diagnostic test not found")

    if test.centre_id != payload.centre_id:
        raise HTTPException(status_code=400, detail="Selected test is not offered by this centre")

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
    return booking


@app.get("/bookings/", response_model=PaginatedResponse[BookingRead])
@limiter.limit("20/minute")
def list_bookings(request: Request, page: int = 1, size: int = 10, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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


@app.get("/bookings/{booking_id}", response_model=BookingRead)
@limiter.limit("20/minute")
def get_booking(request: Request, booking_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this booking")
    return booking


@app.post("/payments/", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_payment(request: Request, payload: PaymentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Invalid booking ID")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to process this booking")
    if abs(booking.amount - payload.amount) > 0.01:
        raise HTTPException(status_code=400, detail="Payment amount does not match booking amount")

    if db.query(Payment).filter(Payment.booking_id == booking.id).first():
        raise HTTPException(status_code=400, detail="Payment already exists for this booking")

    simulated_status = PaymentStatus.SUCCESS if datetime.utcnow().microsecond % 2 == 0 else PaymentStatus.FAILED
    payment = Payment(
        booking_id=booking.id,
        provider=payload.provider,
        amount=payload.amount,
        status=simulated_status,
        external_reference=f"pay_{booking.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
    )
    db.add(payment)

    if simulated_status == PaymentStatus.SUCCESS:
        booking.status = BookingStatus.CONFIRMED
    else:
        booking.status = BookingStatus.FAILED
    db.commit()
    db.refresh(payment)
    return payment


@app.post("/payments/webhook/", response_model=PaymentWebhookResponse)
@limiter.limit("20/minute")
def payment_webhook(request: Request, payload: PaymentWebhookEvent, db: Session = Depends(get_db)):
    existing_event = db.query(WebhookEvent).filter(WebhookEvent.event_id == payload.event_id).first()
    if existing_event:
        return PaymentWebhookResponse(message="Duplicate webhook event ignored", processed=False, idempotent=True)

    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Invalid booking ID")

    payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
    if payment is None:
        payment = Payment(
            booking_id=booking.id,
            provider=payload.provider,
            amount=booking.amount,
            status=PaymentStatus.PENDING,
            external_reference=payload.external_reference,
        )
        db.add(payment)

    if payload.status == "SUCCESS":
        payment.status = PaymentStatus.SUCCESS
        booking.status = BookingStatus.CONFIRMED
    elif payload.status == "FAILED":
        payment.status = PaymentStatus.FAILED
        booking.status = BookingStatus.FAILED
    else:
        raise HTTPException(status_code=400, detail="Unsupported payment status")

    payload_record = WebhookEvent(
        event_id=payload.event_id,
        event_type=payload.event_type,
        payload=payload.model_dump_json(),
    )
    db.add(payload_record)
    db.commit()
    return PaymentWebhookResponse(message="Payment webhook processed successfully", processed=True, idempotent=False)


@app.patch("/bookings/{booking_id}/cancel")
@limiter.limit("5/minute")
def cancel_booking(request: Request, booking_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")
    if booking.status in {BookingStatus.CANCELLED, BookingStatus.CONFIRMED}:
        raise HTTPException(status_code=400, detail="Booking cannot be cancelled in its current state")
    booking.status = BookingStatus.CANCELLED
    db.commit()
    return {"message": "Booking cancelled successfully", "booking_id": booking.id}
