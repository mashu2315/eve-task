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
- GET /centres/  *(supports `?page=1&size=10` pagination)*
- GET /centres/{centre_id}

### Diagnostic Tests

- POST /centres/{centre_id}/tests/
- GET /tests/ *(supports `?page=1&size=10` pagination)*
- GET /tests/{test_id}

### Bookings

- POST /bookings/
- GET /bookings/ *(supports `?page=1&size=10` pagination)*
- GET /bookings/{booking_id}
- PATCH /bookings/{booking_id}/cancel

### Payments

- POST /payments/
- POST /payments/webhook/

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

## Rate Limiting

This project uses `slowapi` to restrict the number of requests clients can make to the endpoints. For example, login and signup are limited to `10/minute` and `5/minute` respectively. Check `app/main.py` for endpoint-specific limits.

## If I Had More Time

- Add Redis caching for centre/test reads
- Add Celery workers for async payment or webhook processing
- Add unit/integration tests for negative cases and authorization rules
- Improve logging and monitoring
- Add retry handling and dead-letter queue patterns for webhook retries

## Running Tests

To run tests, you can execute them directly (ensure your environment or container has `pytest`):

```bash
pytest -q
```
