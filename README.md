# Diagnostic Booking Service

A small FastAPI backend for booking diagnostic tests and simulating payments. It includes user authentication, diagnostic centre/test management, bookings, simulated payments, idempotent payment webhooks, rate limiting, and pagination.

## Features

- User signup and login with JWT authentication
- Diagnostic centre and test management APIs with pagination
- Booking creation and retrieval for authenticated users
- Simulated payment processing with status updates
- Idempotent payment webhook handling
- Basic validation and authorization checks
- Rate limiting to protect endpoints
- Redis caching for list endpoints (`fastapi-cache2`)
- Structured logging with `loguru`
- Retry handling for database transactions in webhooks using `tenacity`


## Architecture & Refactoring

This project follows a clean, modular structure standard for FastAPI applications:
- **`app/main.py`**: The application entry point (initializes app, loads cache/limiters, attaches exception handlers, and mounts routers).
- **`app/routers/`**: Contains the business logic split by domain (`auth.py`, `diagnostics.py`, `bookings.py`, `payments.py`).
- **`app/exceptions.py`**: Defines custom exception classes (e.g., `DiagnosticAppException`) and global handlers to ensure graceful, user-friendly JSON error responses that often include actionable resolutions.
- **`app/schemas.py` & `app/models.py`**: Pydantic schemas and SQLAlchemy DB models.

## Tech Stack

- FastAPI
- SQLAlchemy + PostgreSQL
- JWT authentication
- Pydantic validation
- pytest for API tests
- slowapi for Rate Limiting
- Docker & Docker Compose

## Local Setup with Docker (Recommended)

1. Copy the environment example and update values if needed:
   ```bash
   cp .env.example .env
   ```

2. Start the application and database using Docker Compose:
   ```bash
   docker-compose up --build
   ```

3. Open Swagger UI:
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
  ```json
  {
    "name": "City Lab",
    "location": "Downtown",
    "phone": "123456"
  }
  ```
- GET /centres/  *(supports `?page=1&size=10` pagination)*
- GET /centres/{centre_id}

### Diagnostic Tests

- POST /centres/{centre_id}/tests/
  ```json
  {
    "name": "Blood Test",
    "description": "Routine blood analysis",
    "price": 120.0
  }
  ```
- GET /tests/ *(supports `?page=1&size=10` pagination)*
- GET /tests/{test_id}

### Bookings

- POST /bookings/
  ```json
  {
    "test_id": 1,
    "centre_id": 1,
    "appointment_datetime": "2026-10-02T10:30:00Z"
  }
  ```
- GET /bookings/ *(supports `?page=1&size=10` pagination)*
- GET /bookings/{booking_id}
- PATCH /bookings/{booking_id}/cancel

### Payments

- POST /payments/
  ```json
  {
    "booking_id": 1,
    "amount": 120.0,
    "provider": "mock-provider"
  }
  ```
- POST /payments/webhook/
  ```json
  {
    "event_id": "evt_001",
    "event_type": "payment.success",
    "booking_id": 1,
    "status": "SUCCESS",
    "external_reference": "ref_001",
    "provider": "mock-provider"
  }
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

## Pagination

List endpoints (like GET centres, tests, and bookings) now return a paginated response using `page` and `size` parameters. 

Example response:
```json
{
  "items": [...],
  "page": 1,
  "size": 10,
  "total_pages": 5,
  "total_items": 50
}
```


## Advanced Features Added

### Redis Caching
List endpoints (`/centres/` and `/tests/`) use `fastapi-cache2` to cache results for 60 seconds, drastically reducing database load for frequent queries. The app automatically falls back to an in-memory cache if Redis is unavailable.

### Structured Logging
We use `loguru` configured to emit JSON-formatted structured logs. This is highly beneficial for downstream log aggregators (like ELK, Datadog) to parse events easily.

### Retry Handling
Webhook processing utilizes `tenacity` (`@retry`) to automatically retry on database transaction failures with exponential backoff (up to 3 attempts).

## Rate Limiting

This project uses `slowapi` to restrict the number of requests clients can make to the endpoints. For example, login and signup are limited to `10/minute` and `5/minute` respectively. Check `app/main.py` for endpoint-specific limits.

## If I Had More Time

- Add Celery workers for async payment or webhook processing

## Running Tests

To run tests, you can execute them directly (ensure your environment or container has `pytest`):

```bash
pytest -q
```
