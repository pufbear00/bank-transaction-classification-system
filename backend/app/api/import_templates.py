"""Import Templates CRUD API."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.import_template import ImportTemplate
from app.schemas.import_template import (
    ImportTemplateCreate, ImportTemplateUpdate, ImportTemplateResponse,
)

router = APIRouter(prefix="/import-templates", tags=["import-templates"])


@router.get("", response_model=List[ImportTemplateResponse])
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ImportTemplate).order_by(ImportTemplate.id))
    return [ImportTemplateResponse.model_validate(t) for t in result.scalars().all()]


@router.post("", response_model=ImportTemplateResponse)
async def create_template(data: ImportTemplateCreate, db: AsyncSession = Depends(get_db)):
    template = ImportTemplate(**data.model_dump())
    db.add(template)
    await db.flush()
    return ImportTemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=ImportTemplateResponse)
async def update_template(
    template_id: int, data: ImportTemplateUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ImportTemplate).where(ImportTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(template, k, v)

    return ImportTemplateResponse.model_validate(template)


@router.delete("/{template_id}")
async def delete_template(template_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ImportTemplate).where(ImportTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    return {"deleted": True}
