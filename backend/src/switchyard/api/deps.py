from __future__ import annotations

from typing import Annotated, AsyncGenerator
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.db import get_db_session
from ..core.errors import UnauthorizedException
from ..core.llm import LLMClient, llm_client
from ..core.security import decode_token

AsyncSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user_token(authorization: Annotated[str | None, Header()] = None) -> dict[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException("Missing or invalid Authorization header")
    token = authorization.split(" ")[1]
    try:
        payload = decode_token(token)
        return payload
    except Exception as exc:
        raise UnauthorizedException(f"Invalid authentication token: {exc}") from exc


def get_llm() -> LLMClient:
    return llm_client
