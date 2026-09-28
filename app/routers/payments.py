from datetime import datetime
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.db import get_db
from app.models import Booking, BookingStatus, Payment, PaymentStatus, WebhookEvent, User
from app.schemas import PaymentCreate, PaymentRead, PaymentWebhookEvent, PaymentWebhookResponse
from app.security import get_current_user
from app.exceptions import DiagnosticAppException
from app.limiter import limiter

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/", response_model=PaymentRead, status_code=status.HTTP_201_CREATED, summary="Initiate a Payment")
@limiter.limit("5/minute")
def create_payment(request: Request, payload: PaymentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    
    if not booking:
        raise DiagnosticAppException(f"Invalid booking ID {payload.booking_id}.", status_code=404)
    if booking.user_id != current_user.id:
        raise DiagnosticAppException("You are not authorized to process a payment for this booking.", status_code=403)
    if abs(booking.amount - payload.amount) > 0.01:
        raise DiagnosticAppException(
            message=f"Payment amount ({payload.amount}) does not match booking amount ({booking.amount}).",
            status_code=400,
            resolution="Please provide the exact amount required for the booking."
        )

    if db.query(Payment).filter(Payment.booking_id == booking.id).first():
        raise DiagnosticAppException("A payment already exists for this booking.", status_code=400)

    # Simulation logic for mock payment
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
    logger.info(f"Payment {payment.id} processed for booking {booking.id} with status {simulated_status}")
    return payment

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def process_webhook_db(payload: PaymentWebhookEvent, db: Session):
    existing_event = db.query(WebhookEvent).filter(WebhookEvent.event_id == payload.event_id).first()
    if existing_event:
        logger.info(f"Duplicate webhook {payload.event_id} ignored.")
        return PaymentWebhookResponse(message="Duplicate webhook event ignored", processed=False, idempotent=True)

    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if not booking:
        logger.error(f"Webhook processing failed: Booking {payload.booking_id} not found.")
        raise DiagnosticAppException(f"Invalid booking ID {payload.booking_id}.", status_code=404)

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
        logger.error(f"Webhook processing failed: Unsupported status {payload.status}.")
        raise DiagnosticAppException(f"Unsupported payment status: {payload.status}.", status_code=400)

    payload_record = WebhookEvent(
        event_id=payload.event_id,
        event_type=payload.event_type,
        payload=payload.model_dump_json(),
    )
    db.add(payload_record)
    db.commit()
    
    logger.info(f"Successfully processed webhook event {payload.event_id}")
    return PaymentWebhookResponse(message="Payment webhook processed successfully", processed=True, idempotent=False)

@router.post("/webhook/", response_model=PaymentWebhookResponse, summary="Process Payment Webhook")
@limiter.limit("20/minute")
def payment_webhook(request: Request, payload: PaymentWebhookEvent, db: Session = Depends(get_db)):
    """Handles incoming webhook events from payment providers."""
    logger.info(f"Received webhook event {payload.event_id}")
    return process_webhook_db(payload, db)
