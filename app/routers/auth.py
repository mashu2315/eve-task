from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from loguru import logger

from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, Token
from app.security import create_access_token, hash_password, verify_password
from app.exceptions import DiagnosticAppException
from app.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", status_code=status.HTTP_201_CREATED, summary="Register a new user")
@limiter.limit("5/minute")
def signup(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    """Creates a new user account with the provided details."""
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise DiagnosticAppException(
            message="A user with this email address already exists.",
            status_code=400,
            resolution="Try logging in or use a different email address."
        )

    user = User(
        full_name=payload.full_name.strip(),
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"New user signed up: {user.email}")
    return {"message": "User created successfully", "user_id": user.id}

@router.post("/login", response_model=Token, summary="Login with JSON payload")
@limiter.limit("10/minute")
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticates a user and returns a JWT access token."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise DiagnosticAppException(
            message="Invalid email or password.",
            status_code=401,
            resolution="Please check your credentials and try again."
        )

    access_token = create_access_token({"sub": str(user.id)})
    logger.info(f"User logged in: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token, summary="Login with Form Data (OAuth2 compatible)")
@limiter.limit("10/minute")
def login_form(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 compatible token login, providing an access token for Swagger UI."""
    user = db.query(User).filter(User.email == form_data.username.lower()).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise DiagnosticAppException(
            message="Incorrect username or password.",
            status_code=401,
            resolution="Please verify your credentials."
        )
    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
