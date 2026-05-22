import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_manager_or_above
from app.models.client import Client
from app.models.project import Project, ProjectPhoto, ProjectUpdate
from app.models.quotation import Quotation
from app.models.user import User
from app.models.expense import Expense
from app.schemas.project import (
    ProjectCreate,
    ProjectListItem,
    ProjectOut,
    ProjectUpdate as ProjectUpdateSchema,
    ProjectUpdateCreate,
)
from app.services.cloudinary_service import upload_to_cloudinary

router = APIRouter(prefix="/api/projects", tags=["projects"])

VALID_STAGES = ["not_started", "in_progress", "on_hold", "completed", "invoiced"]


@router.get("", response_model=list[ProjectListItem])
async def list_projects(
    stage: str | None = None,
    assigned_to: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all projects (filtered by role)"""
    query = select(Project).where(Project.organization_id == current_user.organization_id)
    
    # Field agents only see their assigned projects
    if current_user.role == "field_agent":
        query = query.where(Project.assigned_to == current_user.id)
    elif assigned_to:
        query = query.where(Project.assigned_to == uuid.UUID(assigned_to))
    
    if stage:
        query = query.where(Project.stage == stage)
    
    query = query.order_by(Project.updated_at.desc())
    result = await db.execute(query)
    projects = result.scalars().all()
    
    # Add last_update_at from updates
    output = []
    for proj in projects:
        updates_result = await db.execute(
            select(ProjectUpdate.created_at)
            .where(ProjectUpdate.project_id == proj.id)
            .order_by(ProjectUpdate.created_at.desc())
            .limit(1)
        )
        last_update = updates_result.scalar_one_or_none()
        
        output.append(ProjectListItem(
            id=proj.id,
            quotation_id=proj.quotation_id,
            client_id=proj.client_id,
            assigned_to=proj.assigned_to,
            stage=proj.stage,
            title=proj.title,
            target_date=proj.target_date,
            updated_at=proj.updated_at,
            last_update_at=last_update
        ))
    
    return output


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(require_manager_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project from an accepted quotation"""
    # Verify quotation exists and is accepted
    result = await db.execute(
        select(Quotation).where(
            Quotation.id == payload.quotation_id,
            Quotation.organization_id == current_user.organization_id
        )
    )
    quotation = result.scalar_one_or_none()
    
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    
    if quotation.status != "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only accepted quotations can become projects"
        )
    
    # Check if project already exists for this quotation
    existing = await db.execute(
        select(Project).where(Project.quotation_id == payload.quotation_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project already exists for this quotation"
        )
    
    project = Project(
        id=uuid.uuid4(),
        organization_id=current_user.organization_id,
        quotation_id=payload.quotation_id,
        client_id=quotation.client_id,
        assigned_to=payload.assigned_to,
        title=payload.title,
        description=payload.description,
        target_date=payload.target_date,
        stage="not_started"
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return project


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project details with updates and photos"""
    result = await db.execute(
        select(Project)
        .where(Project.id == uuid.UUID(project_id))
        .options(
            selectinload(Project.updates),
            selectinload(Project.photos)
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Field agents can only see their assigned projects
    if current_user.role == "field_agent" and project.assigned_to != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    payload: ProjectUpdateSchema,
    current_user: User = Depends(require_manager_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Update project details"""
    result = await db.execute(
        select(Project).where(
            Project.id == uuid.UUID(project_id),
            Project.organization_id == current_user.organization_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    if payload.stage is not None:
        if payload.stage not in VALID_STAGES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid stage. Must be one of: {', '.join(VALID_STAGES)}"
            )
        project.stage = payload.stage
        if payload.stage == "completed" and not project.completed_at:
            project.completed_at = datetime.now(timezone.utc)
    
    if payload.assigned_to is not None:
        project.assigned_to = payload.assigned_to
    
    if payload.title is not None:
        project.title = payload.title
    
    if payload.description is not None:
        project.description = payload.description
    
    if payload.target_date is not None:
        project.target_date = payload.target_date
    
    await db.commit()
    await db.refresh(project)
    return project


@router.post("/{project_id}/updates", status_code=status.HTTP_201_CREATED)
async def post_update(
    project_id: str,
    payload: ProjectUpdateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Post a progress update to a project"""
    result = await db.execute(
        select(Project).where(Project.id == uuid.UUID(project_id))
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Field agents can only update their assigned projects
    if current_user.role == "field_agent" and project.assigned_to != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    update = ProjectUpdate(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=current_user.organization_id,
        posted_by=current_user.id,
        body=payload.body
    )
    
    db.add(update)
    project.updated_at = datetime.now(timezone.utc)
    await db.commit()
    
    return {"message": "Update posted"}


@router.post("/{project_id}/photos", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    project_id: str,
    file: UploadFile = File(...),
    caption: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a photo to a project"""
    result = await db.execute(
        select(Project).where(Project.id == uuid.UUID(project_id))
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    if project.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Field agents can only upload to their assigned projects
    if current_user.role == "field_agent" and project.assigned_to != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed"
        )
    
    # Upload to Cloudinary
    folder = f"kastra/{current_user.organization_id}/projects/{project_id}"
    try:
        cloudinary_url = await upload_to_cloudinary(file.file, folder)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload photo: {str(e)}"
        )
    
    photo = ProjectPhoto(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=current_user.organization_id,
        uploaded_by=current_user.id,
        cloudinary_url=cloudinary_url,
        caption=caption
    )
    
    db.add(photo)
    project.updated_at = datetime.now(timezone.utc)
    await db.commit()
    
    return {"message": "Photo uploaded", "url": cloudinary_url}


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(require_manager_or_above),
    db: AsyncSession = Depends(get_db)
):
    """Delete a project"""
    result = await db.execute(
        select(Project).where(
            Project.id == uuid.UUID(project_id),
            Project.organization_id == current_user.organization_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    await db.delete(project)
    await db.commit()
    return {"message": "Project deleted"}


@router.get("/{project_id}/financials")
async def get_project_financials(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get project financial summary: revenue, expenses, profit"""
    result = await db.execute(
        select(Project).where(
            Project.id == uuid.UUID(project_id),
            Project.organization_id == current_user.organization_id
        ).options(selectinload(Project.quotation))
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    # Get revenue from quotation
    quotation_result = await db.execute(
        select(Quotation).where(Quotation.id == project.quotation_id)
    )
    quotation = quotation_result.scalar_one_or_none()
    revenue = float(quotation.grand_total) if quotation else 0.0
    
    # Get total expenses for this project
    expenses_result = await db.execute(
        select(func.sum(Expense.amount))
        .where(Expense.project_id == uuid.UUID(project_id))
    )
    total_expenses = expenses_result.scalar_one_or_none() or 0.0
    total_expenses = float(total_expenses)
    
    profit = revenue - total_expenses
    margin = (profit / revenue * 100) if revenue > 0 else 0.0
    
    return {
        "revenue": revenue,
        "expenses": total_expenses,
        "profit": profit,
        "margin": round(margin, 2)
    }
