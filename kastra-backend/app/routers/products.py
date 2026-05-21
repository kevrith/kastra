import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.client_price import ClientPrice
from app.models.product import Product
from app.models.user import User
from app.schemas.common import MessageResponse, Response

router = APIRouter(prefix="/api/products", tags=["products"])


class ProductIn(BaseModel):
    name: str
    description: str | None = None
    unit_price: float


class ProductOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    unit_price: float
    client_price: float | None = None  # client-specific agreed price, if known

    model_config = {"from_attributes": True}


@router.get("", response_model=list[ProductOut])
async def list_products(
    q: str | None = Query(None, description="Search by name"),
    client_id: uuid.UUID | None = Query(None, description="Return client-specific pricing when available"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Product).where(Product.organization_id == current_user.organization_id)
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%"))
    rows = (await db.execute(stmt.order_by(Product.name))).scalars().all()

    if not client_id or not rows:
        return rows

    # Fetch client-specific prices for the matched product names
    names = [p.name for p in rows]
    cp_result = await db.execute(
        select(ClientPrice).where(
            ClientPrice.organization_id == current_user.organization_id,
            ClientPrice.client_id == client_id,
            ClientPrice.description.in_(names),
        )
    )
    client_prices = {cp.description: float(cp.unit_price) for cp in cp_result.scalars().all()}

    # Inject client_price into the response without mutating ORM objects
    out = []
    for p in rows:
        d = ProductOut.model_validate(p)
        d.client_price = client_prices.get(p.name)
        out.append(d)
    return out


@router.post("", response_model=Response[ProductOut], status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prod = Product(
        organization_id=current_user.organization_id,
        name=payload.name,
        description=payload.description,
        unit_price=payload.unit_price,
    )
    db.add(prod)
    await db.flush()
    await db.refresh(prod)
    return Response(data=prod)


@router.put("/{product_id}", response_model=Response[ProductOut])
async def update_product(
    product_id: uuid.UUID,
    payload: ProductIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prod = await db.get(Product, product_id)
    if not prod or prod.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Product not found")
    prod.name = payload.name
    prod.description = payload.description
    prod.unit_price = payload.unit_price
    await db.flush()
    await db.refresh(prod)
    return Response(data=prod)


@router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prod = await db.get(Product, product_id)
    if not prod or prod.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.delete(prod)
    return MessageResponse(message="Product deleted")
