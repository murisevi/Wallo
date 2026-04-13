import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    currency: str
    created_at: datetime


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2)
    email: EmailStr | None = None
    currency: Literal["EUR", "USD", "GBP"] | None = None


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    email: str
    full_name: str = Field(validation_alias="name")
    currency: str
    timezone: str = "Europe/Madrid"
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
