import math
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.expense import Expense
from app.models.user import User
from app.schemas.common import Meta, PaginatedResponse, Response, MessageResponse

router = APIRouter(prefix="/api/expenses", tags=["expenses"])

CATEGORIES = ["rent", "salaries", "utilities", "supplies", "transport", "marketing", "other"]


class ExpenseIn(BaseModel):
    category: str
    description: str
    vendor: str | None = None
    amount: float
    date: date
    project_id: uuid.UUID | None = None


class ExpenseOut(BaseModel):
    id: uuid.UUID
    category: str
    description: str
    vendor: str | None
    amount: float
    date: date
    project_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=PaginatedResponse[ExpenseOut])
async def list_expenses(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Expense).where(Expense.organization_id == current_user.organization_id)
    if category:
        q = q.where(Expense.category == category)
    if from_date:
        q = q.where(Expense.date >= from_date)
    if to_date:
        q = q.where(Expense.date <= to_date)
    if project_id:
        q = q.where(Expense.project_id == uuid.UUID(project_id))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.order_by(Expense.date.desc()).offset((page - 1) * limit).limit(limit))).scalars().all()

    return PaginatedResponse(
        data=rows,
        meta=Meta(page=page, limit=limit, total=total, pages=math.ceil(total / limit) or 1),
    )


@router.post("", response_model=Response[ExpenseOut], status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: ExpenseIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exp = Expense(
        organization_id=current_user.organization_id,
        project_id=payload.project_id,
        category=payload.category,
        description=payload.description,
        vendor=payload.vendor,
        amount=payload.amount,
        date=payload.date,
    )
    db.add(exp)
    await db.flush()
    await db.refresh(exp)
    return Response(data=exp)


@router.put("/{expense_id}", response_model=Response[ExpenseOut])
async def update_expense(
    expense_id: uuid.UUID,
    payload: ExpenseIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exp = await db.get(Expense, expense_id)
    if not exp or exp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Expense not found")
    exp.category = payload.category
    exp.description = payload.description
    exp.vendor = payload.vendor
    exp.amount = payload.amount
    exp.date = payload.date
    exp.project_id = payload.project_id
    await db.flush()
    await db.refresh(exp)
    return Response(data=exp)


@router.delete("/{expense_id}", response_model=MessageResponse)
async def delete_expense(
    expense_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exp = await db.get(Expense, expense_id)
    if not exp or exp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Expense not found")
    await db.delete(exp)
    return MessageResponse(message="Expense deleted")


@router.get("/summary/monthly", response_model=dict)
async def monthly_expense_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns total expenses grouped by category for the current month."""
    from sqlalchemy import extract
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    rows = (await db.execute(
        select(Expense.category, func.sum(Expense.amount).label("total"))
        .where(
            Expense.organization_id == current_user.organization_id,
            extract("year", Expense.date) == now.year,
            extract("month", Expense.date) == now.month,
        )
        .group_by(Expense.category)
    )).all()
    total = sum(r.total for r in rows)
    return {"month_total": float(total), "by_category": {r.category: float(r.total) for r in rows}}
