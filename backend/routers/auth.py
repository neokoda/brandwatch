from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.auth import verify_password, create_access_token, get_current_user
from backend.models.account import User
from backend.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    await db.refresh(user, ["account"])
    token = create_access_token(str(user.id), str(user.account_id))
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        account_id=str(user.account_id),
        account_name=user.account.name,
        account_slug=user.account.slug,
        role=user.role,
    )


@router.get("/me")
async def me(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.refresh(current_user, ["account"])
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "account_id": str(current_user.account_id),
        "account_name": current_user.account.name,
        "account_slug": current_user.account.slug,
    }
