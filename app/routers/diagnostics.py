import math
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from fastapi_cache.decorator import cache
from loguru import logger

from app.db import get_db
from app.models import DiagnosticCentre, DiagnosticTest
from app.schemas import DiagnosticCentreCreate, DiagnosticCentreRead, DiagnosticTestCreate, DiagnosticTestRead, PaginatedResponse
from app.exceptions import DiagnosticAppException
from app.limiter import limiter

router = APIRouter(tags=["Diagnostics"])

@router.post("/centres/", response_model=DiagnosticCentreRead, status_code=status.HTTP_201_CREATED, summary="Create a Diagnostic Centre")
@limiter.limit("10/minute")
def create_centre(request: Request, payload: DiagnosticCentreCreate, db: Session = Depends(get_db)):
    centre = DiagnosticCentre(name=payload.name.strip(), location=payload.location.strip(), phone=payload.phone)
    db.add(centre)
    db.commit()
    db.refresh(centre)
    logger.info(f"Created new diagnostic centre: {centre.name}")
    return centre

@router.get("/centres/", response_model=PaginatedResponse[DiagnosticCentreRead], summary="List Diagnostic Centres")
@limiter.limit("20/minute")
@cache(expire=60)
def list_centres(request: Request, page: int = 1, size: int = 10, db: Session = Depends(get_db)):
    if page < 1 or size < 1:
        raise DiagnosticAppException("Page and size must be strictly positive integers.")
        
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

@router.get("/centres/{centre_id}", response_model=DiagnosticCentreRead, summary="Get Diagnostic Centre Details")
@limiter.limit("20/minute")
@cache(expire=60)
def get_centre(request: Request, centre_id: int, db: Session = Depends(get_db)):
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == centre_id).first()
    if not centre:
        raise DiagnosticAppException(
            message=f"Diagnostic centre with ID {centre_id} not found.",
            status_code=404
        )
    return centre

@router.post("/centres/{centre_id}/tests/", response_model=DiagnosticTestRead, status_code=status.HTTP_201_CREATED, summary="Create a Test for a Centre")
@limiter.limit("10/minute")
def create_test_for_centre(request: Request, centre_id: int, payload: DiagnosticTestCreate, db: Session = Depends(get_db)):
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == centre_id).first()
    if not centre:
        raise DiagnosticAppException(f"Diagnostic centre with ID {centre_id} not found.", status_code=404)

    test = DiagnosticTest(
        name=payload.name.strip(),
        description=payload.description,
        price=payload.price,
        centre_id=centre_id,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    logger.info(f"Created new test '{test.name}' for centre {centre_id}")
    return test

@router.get("/tests/", response_model=PaginatedResponse[DiagnosticTestRead], summary="List Diagnostic Tests")
@limiter.limit("20/minute")
@cache(expire=60)
def list_tests(request: Request, page: int = 1, size: int = 10, db: Session = Depends(get_db)):
    if page < 1 or size < 1:
        raise DiagnosticAppException("Page and size must be strictly positive integers.")
        
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

@router.get("/tests/{test_id}", response_model=DiagnosticTestRead, summary="Get Test Details")
@limiter.limit("20/minute")
@cache(expire=60)
def get_test(request: Request, test_id: int, db: Session = Depends(get_db)):
    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == test_id).first()
    if not test:
        raise DiagnosticAppException(f"Diagnostic test with ID {test_id} not found.", status_code=404)
    return test
