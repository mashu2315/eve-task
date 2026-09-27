# Diagnostic Booking Service

A small FastAPI backend for booking diagnostic tests and simulating payments. It includes user authentication, diagnostic centre/test management, bookings, simulated payments, and idempotent payment webhooks.

## Features

- User signup and login with JWT authentication
- Diagnostic centre and test management APIs
- Booking creation and retrieval for authenticated users
- Simulated payment processing with status updates
- Idempotent payment webhook handling
- Basic validation and authorization checks

## Tech Stack

- FastAPI
- SQLAlchemy + SQLite by default (PostgreSQL-ready)
- JWT authentication
- Pydantic validation
- pytest for API tests

## Local Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment example and update values if needed:
   ```bash
   cp .env.example .env
   ```

4. Run the app:
   ```bash
   uvicorn app.main:app --reload
   ```

5. Open Swagger UI:
   - http://127.0.0.1:8000/docs

## API Endpoints

### Authentication

- POST /auth/signup
  ```json
  {
    "full_name": "Alice Sam",
    "email": "alice@example.com",
    "password": "myPassword123"
  }
  ```

- POST /auth/login
  ```json
  {
    "email": "alice@example.com",
    "password": "myPassword123"
  }
  ```

- Response:
  ```json
  {
    "access_token": "<jwt>",
    "token_type": "bearer"
  }
  ```

### Diagnostic Centres

- POST /centres/
- GET /centres/
- GET /centres/{centre_id}

Example:
```bash
curl -X POST http://127.0.0.1:8000/centres/ \
  -H "Content-Type: application/json" \
  -d '{"name":"City Lab","location":"Downtown","phone":"123456"}'
```

### Diagnostic Tests

- POST /centres/{centre_id}/tests/
- GET /tests/
- GET /tests/{test_id}

Example:
```bash
curl -X POST http://127.0.0.1:8000/centres/1/tests/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Blood Test","description":"Routine blood analysis","price":120.0}'
```

### Bookings

- POST /bookings/
- GET /bookings/
- GET /bookings/{booking_id}
- PATCH /bookings/{booking_id}/cancel

Example:
```bash
curl -X POST http://127.0.0.1:8000/bookings/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "test_id": 1,
    "centre_id": 1,
    "appointment_datetime": "2026-10-02T10:30:00"
  }'
```

### Payments

- POST /payments/
- POST /payments/webhook/

Example payment:
```bash
curl -X POST http://127.0.0.1:8000/payments/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"booking_id": 1, "amount": 120.0, "provider": "mock-provider"}'
```

Example webhook:
```bash
curl -X POST http://127.0.0.1:8000/payments/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "evt_001",
    "event_type": "payment.success",
    "booking_id": 1,
    "status": "SUCCESS",
    "external_reference": "ref_001",
    "provider": "mock-provider"
  }'
```

## Database / Schema Design

The application uses SQLAlchemy models:

- `users`: stores account details and hashed passwords.
- `diagnostic_centres`: stores centre metadata such as `name`, `location`, and `phone`.
- `diagnostic_tests`: records test information, price, and centre association.
- `bookings`: records patient, test, centre, appointment time, amount, and status.
- `payments`: stores payment attempt details per booking.
- `webhook_events`: stores processed webhook IDs to enforce idempotency.

Relationships:
- One user can have many bookings.
- One centre can offer many tests and bookings.
- One test belongs to one centre but may appear in many bookings.
- One booking has at most one payment.
- Webhooks are deduplicated by `event_id`.

## Important Assumptions

- SQLite is used by default for local development simplicity; PostgreSQL can be swapped in by changing `DATABASE_URL`.
- The mock payment endpoint randomly returns `SUCCESS` or `FAILED` for simulation purposes.
- Webhook processing is deduplicated by `event_id` to guarantee idempotency.
- Only the booking owner can view or cancel their bookings.

## Edge Cases Covered

- Invalid or missing booking IDs
- Unauthorized access to another user's booking
- Repeated webhook events
- Payment amount mismatch
- Repayment of failed payments
- Invalid or expired JWT
- Booking date in the past

## If I Had More Time

- Add PostgreSQL and Docker Compose setup with real database service
- Add Redis caching for centre/test reads
- Add Celery workers for async payment or webhook processing
- Implement pagination and rate limiting
- Add unit/integration tests for negative cases and authorization rules
- Improve logging and monitoring
- Add retry handling and dead-letter queue patterns for webhook retries

## Running Tests

```bash
pytest -q
```
