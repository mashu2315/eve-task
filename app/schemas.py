from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


class DiagnosticTestBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    price: float = Field(..., gt=0)


class DiagnosticTestCreate(DiagnosticTestBase):
    pass


class DiagnosticTestRead(DiagnosticTestBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    centre_id: int


class DiagnosticCentreBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    location: str = Field(..., min_length=2, max_length=200)
    phone: Optional[str] = None


class DiagnosticCentreCreate(DiagnosticCentreBase):
    pass


class DiagnosticCentreRead(DiagnosticCentreBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tests: List[DiagnosticTestRead] = []


class BookingCreate(BaseModel):
    test_id: int
    centre_id: int
    appointment_datetime: datetime

    @model_validator(mode="after")
    def validate_booking(self):
        appointment_dt = self.appointment_datetime
        if appointment_dt.tzinfo is None:
            appointment_dt = appointment_dt.replace(tzinfo=timezone.utc)
        else:
            appointment_dt = appointment_dt.astimezone(timezone.utc)

        if appointment_dt <= datetime.now(timezone.utc):
            raise ValueError("Appointment date/time must be in the future.")
        return self


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    test_id: int
    centre_id: int
    appointment_datetime: datetime
    amount: float
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class PaymentCreate(BaseModel):
    booking_id: int
    amount: float = Field(..., gt=0)
    provider: str = "mock-provider"


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    booking_id: int
    provider: str
    amount: float
    status: str
    external_reference: Optional[str] = None


class PaymentWebhookEvent(BaseModel):
    event_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    booking_id: int
    status: str = Field(..., pattern="^(SUCCESS|FAILED)$")
    external_reference: Optional[str] = None
    provider: str = "mock-provider"


class PaymentWebhookResponse(BaseModel):
    message: str
    processed: bool
    idempotent: bool = False
