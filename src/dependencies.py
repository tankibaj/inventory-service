import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session


async def get_tenant_id(x_tenant_id: Annotated[str, Header()]) -> uuid.UUID:
    return uuid.UUID(x_tenant_id)


TenantDep = Annotated[uuid.UUID, Depends(get_tenant_id)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
