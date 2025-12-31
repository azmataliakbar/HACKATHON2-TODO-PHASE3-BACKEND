from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_async_session
from src.models import Task, User
from src.core.security import get_password_hash, verify_password, create_access_token
from src.models import Task, TaskCreate, TaskUpdate, TaskRead
from sqlmodel import select, Field
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import uuid

router = APIRouter()


# Request/Response models
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


@router.post("/auth/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: SignupRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Register a new user."""

    # Check if user already exists
    result = await session.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_pw = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        name=user_data.full_name,
        password_hash=hashed_pw
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    # Generate token
    access_token = create_access_token(data={"user_id": str(new_user.id)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=new_user.id,
            email=new_user.email,
            name=new_user.name
        )
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    user_data: LoginRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Login user and return access token."""

    # Find user
    result = await session.execute(
        select(User).where(User.email == user_data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Generate token
    access_token = create_access_token(data={"user_id": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name
        )
    )