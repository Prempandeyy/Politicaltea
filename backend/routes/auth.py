from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    Token
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)


# =========================================================
# PASSWORD HASHING
# =========================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password must be 72 bytes or fewer."
        )

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed.decode("utf-8")


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    password_bytes = plain_password.encode("utf-8")

    if len(password_bytes) > 72:
        return False

    try:
        return bcrypt.checkpw(
            password_bytes,
            hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def verify_password(
    plain_password: str,
    hashed_password: str
):
    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# =========================================================
# JWT SETTINGS
# =========================================================

SECRET_KEY = "political-tea-secret-key-change-this-later"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


# =========================================================
# CREATE JWT
# =========================================================

def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# =========================================================
# GET CURRENT USER
# =========================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user_id = int(user_id)

    except (JWTError, ValueError):

        raise credentials_exception

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if user is None:
        raise credentials_exception

    return user


# =========================================================
# REGISTER
# =========================================================

@router.post(
    "/register",
    response_model=UserResponse
)
def register(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    # Check if email already exists
    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Hash password
    hashed_password = hash_password(
        user.password
    )

    # Create user
    new_user = User(
        name=user.name,
        email=user.email,
        password=hashed_password,
        state_id=user.state_id
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# =========================================================
# LOGIN
# =========================================================

@router.post(
    "/login",
    response_model=Token
)
def login(
    user: UserLogin,
    db: Session = Depends(get_db)
):

    # Find user
    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if not existing_user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Verify password
    password_correct = verify_password(
        user.password,
        existing_user.password
    )

    if not password_correct:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Create JWT
    access_token = create_access_token({
        "sub": str(existing_user.id)
    })

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# =========================================================
# CURRENT USER
# =========================================================

@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    current_user: User = Depends(get_current_user)
):

    return current_user


# =========================================================
# UPDATE PROFILE
# =========================================================

@router.put(
    "/me",
    response_model=UserResponse
)
def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Validate name
    # -----------------------------------------------------

    if not user_data.name or not user_data.name.strip():

        raise HTTPException(
            status_code=400,
            detail="Name cannot be empty"
        )

    # -----------------------------------------------------
    # Check if email is already used by another user
    # -----------------------------------------------------

    existing_user = db.query(User).filter(
        User.email == user_data.email,
        User.id != current_user.id
    ).first()

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Email already registered by another user"
        )

    # -----------------------------------------------------
    # Update fields
    # -----------------------------------------------------

    current_user.name = user_data.name.strip()
    current_user.email = user_data.email

    if user_data.state_id is not None:
        current_user.state_id = user_data.state_id

    # -----------------------------------------------------
    # Save changes
    # -----------------------------------------------------

    db.commit()
    db.refresh(current_user)

    return current_user


# =========================================================
# LOGOUT
# =========================================================

@router.post("/logout")
def logout():

    return {
        "message": "Logged out successfully"
    }
