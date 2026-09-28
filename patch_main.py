import re

with open('app/main.py', 'r') as f:
    content = f.read()

# Add math import
if 'import math' not in content:
    content = content.replace('from typing import List, Optional', 'import math\nfrom typing import List, Optional')

# Update schemas import
content = content.replace('Token,', 'Token,\n    PaginatedResponse,')

# Replace list_centres
content = re.sub(
    r'@app\.get\("/centres/", response_model=List\[DiagnosticCentreRead\]\)\n@limiter\.limit\("20/minute"\)\ndef list_centres\(request: Request, skip: int = 0, limit: int = 100, db: Session = Depends\(get_db\)\):\n    centres = db\.query\(DiagnosticCentre\)\.offset\(skip\)\.limit\(limit\)\.all\(\)\n    return centres',
    """@app.get("/centres/", response_model=PaginatedResponse[DiagnosticCentreRead])
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
    )""",
    content,
    flags=re.MULTILINE
)

# Replace list_tests
content = re.sub(
    r'@app\.get\("/tests/", response_model=List\[DiagnosticTestRead\]\)\n@limiter\.limit\("20/minute"\)\ndef list_tests\(request: Request, skip: int = 0, limit: int = 100, db: Session = Depends\(get_db\)\):\n    return db\.query\(DiagnosticTest\)\.offset\(skip\)\.limit\(limit\)\.all\(\)',
    """@app.get("/tests/", response_model=PaginatedResponse[DiagnosticTestRead])
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
    )""",
    content,
    flags=re.MULTILINE
)

# Replace list_bookings
content = re.sub(
    r'@app\.get\("/bookings/", response_model=List\[BookingRead\]\)\n@limiter\.limit\("20/minute"\)\ndef list_bookings\(request: Request, skip: int = 0, limit: int = 100, current_user: User = Depends\(get_current_user\), db: Session = Depends\(get_db\)\):\n    bookings = db\.query\(Booking\)\.filter\(Booking\.user_id == current_user\.id\)\.order_by\(Booking\.created_at\.desc\(\)\)\.offset\(skip\)\.limit\(limit\)\.all\(\)\n    return bookings',
    """@app.get("/bookings/", response_model=PaginatedResponse[BookingRead])
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
    )""",
    content,
    flags=re.MULTILINE
)

with open('app/main.py', 'w') as f:
    f.write(content)
