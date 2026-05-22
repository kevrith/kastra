from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    quotation_id: str
    title: str
    description: str | None = None
    assigned_to: UUID | None = None
    target_date: datetime | None = None


class ProjectUpdate(BaseModel):
    assigned_to: UUID | None = None
    stage: str | None = None
    title: str | None = None
    description: str | None = None
    target_date: datetime | None = None


class ProjectUpdateCreate(BaseModel):
    body: str


class ProjectPhotoOut(BaseModel):
    id: UUID
    cloudinary_url: str
    caption: str | None
    uploaded_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectUpdateOut(BaseModel):
    id: UUID
    body: str
    posted_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectOut(BaseModel):
    id: UUID
    organization_id: UUID
    quotation_id: str
    client_id: UUID
    assigned_to: UUID | None
    stage: str
    title: str
    description: str | None
    target_date: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    updates: list[ProjectUpdateOut] = []
    photos: list[ProjectPhotoOut] = []

    class Config:
        from_attributes = True


class ProjectListItem(BaseModel):
    id: UUID
    quotation_id: str
    client_id: UUID
    assigned_to: UUID | None
    stage: str
    title: str
    target_date: datetime | None
    updated_at: datetime
    last_update_at: datetime | None = None

    class Config:
        from_attributes = True
