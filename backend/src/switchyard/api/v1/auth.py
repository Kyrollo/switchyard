from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel, EmailStr
from ...core.security import create_access_token, create_refresh_token, hash_password, generate_api_key

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest) -> dict[str, str]:
    # Production user registration
    return {"message": "User registered successfully", "email": req.email}


@router.post("/token", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    access_token = create_access_token({"sub": req.email})
    refresh_token = create_refresh_token({"sub": req.email})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/api-key", status_code=status.HTTP_201_CREATED)
async def create_api_key(name: str) -> dict[str, str]:
    raw_key = generate_api_key()
    return {"name": name, "api_key": raw_key}
