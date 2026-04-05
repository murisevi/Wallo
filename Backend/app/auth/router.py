from fastapi import APIRouter, status

from app.auth.schemas import TokenResponse, UserCreate, UserLogin, UserResponse
from app.auth.service import authenticate_user, register_user
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
