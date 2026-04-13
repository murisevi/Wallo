from fastapi import APIRouter, status

from app.auth.schemas import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserProfileResponse,
    UserProfileUpdate,
    UserResponse,
)
from app.auth.service import (
    authenticate_user,
    get_user_profile,
    register_user,
    update_user_profile,
)
from app.dependencies import CurrentUser, DbSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(user_data: UserCreate, db: DbSession) -> UserResponse:
    """Create a new user account and return the user profile."""
    user = await register_user(db, user_data)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: DbSession) -> TokenResponse:
    """Authenticate with email and password. Returns a JWT access token."""
    return await authenticate_user(db, credentials.email, credentials.password)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(current_user: CurrentUser, db: DbSession) -> UserProfileResponse:
    """Return the full profile of the authenticated user."""
    return await get_user_profile(db, current_user.id)


@router.patch("/profile", response_model=UserProfileResponse)
async def patch_profile(
    body: UserProfileUpdate, current_user: CurrentUser, db: DbSession
) -> UserProfileResponse:
    """Update name, email, or currency for the authenticated user."""
    return await update_user_profile(db, current_user.id, body)
