from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import bcrypt

from jose import jwt, JWTError
from datetime import datetime, timedelta

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
)


# =========================================
# ROUTER
# =========================================

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


# =========================================
# OAUTH2
# =========================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)


# =========================================
# JWT SETTINGS
# =========================================

SECRET_KEY = "political-tea-secret-key-change-this-later"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


# =========================================
# PASSWORD HASHING
# =========================================

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt directly.

    bcrypt supports maximum 72 bytes.
    We explicitly validate the password instead
    of allowing a server-side 500 error.
    """

    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password must be 72 bytes or fewer.",
        )

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed.decode("utf-8")


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:

    password_bytes = plain_password.encode("utf-8")

    if len(password_bytes) > 72:
        return False

    try:
        return bcrypt.checkpw(
            password_bytes,
            hashed_password.encode("utf-8"),
        )

    except (ValueError, TypeError):
        return False


# =========================================
# CREATE JWT
# =========================================

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
        algorithm=ALGORITHM,
    )


# =========================================
# GET CURRENT USER
# =========================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user_id = int(user_id)

    except (JWTError, ValueError, TypeError):

        raise credentials_exception

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if user is None:
        raise credentials_exception

    return user


# =========================================
# REGISTER
# =========================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user: UserCreate,
    db: Session = Depends(get_db),
):

    # -------------------------------------
    # Check existing email
    # -------------------------------------

    existing_user = (
        db.query(User)
        .filter(User.email == user.email)
        .first()
    )

    if existing_user:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # -------------------------------------
    # Validate password
    # -------------------------------------

    if not user.password:
        raise HTTPException(
            status_code=400,
            detail="Password cannot be empty.",
        )

    if len(user.password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password must be 72 bytes or fewer.",
        )

    # -------------------------------------
    # Hash password
    # -------------------------------------

    hashed_password = hash_password(
        user.password
    )

    # -------------------------------------
    # Create user
    # -------------------------------------

    new_user = User(
        name=user.name,
        email=user.email,
        password=hashed_password,
        state_id=user.state_id,
    )

    try:

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Could not create user: {str(e)}",
        )

    return new_user


# =========================================
# LOGIN
# =========================================

@router.post(
    "/login",
    response_model=Token,
)
def login(
    user: UserLogin,
    db: Session = Depends(get_db),
):

    # -------------------------------------
    # Find user
    # -------------------------------------

    existing_user = (
        db.query(User)
        .filter(User.email == user.email)
        .first()
    )

    if not existing_user:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # -------------------------------------
    # Verify password
    # -------------------------------------

    password_correct = verify_password(
        user.password,
        existing_user.password,
    )

    if not password_correct:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # -------------------------------------
    # Create JWT
    # -------------------------------------

    access_token = create_access_token({
        "sub": str(existing_user.id)
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# =========================================
# CURRENT USER
# =========================================

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):

    return current_user


# =========================================
# LOGOUT
# =========================================

@router.post("/logout")
def logout():

    return {
        "message": "Logged out successfully"
    }
