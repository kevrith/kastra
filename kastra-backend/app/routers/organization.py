from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import User
from app.schemas.common import Response
from app.schemas.organization import OrganizationOut, OrganizationUpdate
from app.services.etims_service import test_connection

router = APIRouter(prefix="/api/organization", tags=["organization"])


@router.get("", response_model=Response[OrganizationOut])
async def get_organization(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return Response(data=OrganizationOut.from_orm_with_flags(org))


@router.put("", response_model=Response[OrganizationOut])
async def update_organization(
    payload: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(org, field, value)

    await db.flush()
    await db.refresh(org)
    return Response(data=OrganizationOut.from_orm_with_flags(org))


@router.post("/etims-test")
async def etims_test_connection(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test KRA eTIMS credentials without submitting an invoice."""
    result = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return await test_connection(org)
