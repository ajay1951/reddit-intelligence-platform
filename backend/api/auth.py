from datetime import datetime, timedelta, timezone
import hmac
from typing import Any, Optional
import structlog

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel, Field

from backend.config import settings
from backend.api.limiter import limiter

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    username: str
    role: str = "user"


class TokenRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    role: Optional[str] = Field("user", pattern="^(user|admin)$")
    secret: Optional[str] = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=100)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    role: str = "user"
) -> str:
    """Create a signed JWT token with strictly validated algorithm and expiration."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
        "role": role,
    })
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> TokenData:
    """Validate bearer token from Authorization header."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": True, "verify_sub": True}
        )
        username: Optional[str] = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims: subject ('sub') is required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        role: str = payload.get("role", "user")
        return TokenData(username=username, role=role)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as exc:
        logger.warning("JWT verification failed", error_type=type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin(
    token: Optional[str] = Depends(oauth2_scheme),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
) -> TokenData:
    """Ensure caller has administrator privileges via JWT role or verified admin key."""
    # 1. Machine-to-machine admin key override if configured (timing-safe comparison)
    if settings.admin_api_key and x_admin_key:
        if hmac.compare_digest(x_admin_key, settings.admin_api_key):
            return TokenData(username="admin_api_key_system", role="admin")

    # 2. JWT bearer token validation
    current_user = await get_current_user(token)
    if current_user and current_user.role == "admin":
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient privileges: admin role required for this operation",
    )



@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login_for_access_token(request: Request, req: TokenRequest) -> Token:
    """
    Generate an access token.
    If requesting an 'admin' role, strictly validates secret against ADMIN_API_KEY.
    """
    requested_role = req.role or "user"
    if requested_role == "admin":
        valid_admin = False
        if settings.admin_api_key and req.secret and hmac.compare_digest(req.secret, settings.admin_api_key):
            valid_admin = True

        if not valid_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid admin credentials for admin role generation"
            )

    expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    token = create_access_token(
        data={"sub": req.username},
        expires_delta=expires_delta,
        role=requested_role
    )
    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login_with_password(request: Request, req: LoginRequest) -> Token:
    """
    Authenticate administrator with username and password.
    Returns signed admin JWT token on success or 401 Unauthorized on failure.
    Uses timing-safe comparison to prevent side-channel timing attacks.
    """
    is_valid = False
    
    # Timing-safe comparison against configured admin credentials
    if (
        hmac.compare_digest(req.username, settings.admin_username)
        and hmac.compare_digest(req.password, settings.admin_password)
    ):
        is_valid = True
    elif settings.admin_api_key and hmac.compare_digest(req.password, settings.admin_api_key):
        is_valid = True

    if not is_valid:
        logger.warning("Admin login attempt failed", username=req.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    token = create_access_token(
        data={"sub": req.username},
        expires_delta=expires_delta,
        role="admin"
    )
    logger.info("Admin user authenticated successfully", username=req.username)
    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60
    )


@router.get("/me")
async def get_me(user: TokenData = Depends(get_current_user)) -> dict:
    return {"username": user.username, "role": user.role}

