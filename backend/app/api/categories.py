"""Categories API: tree + CRUD + cascade lookup."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.models.category_tree import CategoryNode
from app.schemas.category import (
    CategoryNodeCreate, CategoryNodeUpdate,
    CategoryNodeResponse, CategoryTreeNode, CategoryLookupResponse,
)

router = APIRouter(prefix="/categories", tags=["categories"])


def _build_tree(nodes: List[CategoryNode], parent_id: int | None = None) -> List[dict]:
    tree = []
    for node in nodes:
        if node.parent_id == parent_id:
            children = _build_tree(nodes, node.id)
            item = CategoryTreeNode(
                id=node.id,
                name=node.name,
                level=node.level,
                parent_id=node.parent_id,
                cf_line=node.cf_line,
                sort_order=node.sort_order,
                created_at=node.created_at,
                children=[CategoryTreeNode(**c) for c in children],
            )
            tree.append(item.model_dump())
    return tree


@router.get("", response_model=List[CategoryTreeNode])
async def get_category_tree(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CategoryNode).order_by(CategoryNode.sort_order, CategoryNode.id)
    )
    nodes = list(result.scalars().all())
    return _build_tree(nodes, None)


@router.get("/flat", response_model=List[CategoryNodeResponse])
async def get_categories_flat(
    level: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(CategoryNode).order_by(CategoryNode.sort_order, CategoryNode.id)
    if level is not None:
        q = q.where(CategoryNode.level == level)
    result = await db.execute(q)
    return [CategoryNodeResponse.model_validate(n) for n in result.scalars().all()]


@router.get("/lookup/{management_name}", response_model=CategoryLookupResponse)
async def lookup_category(management_name: str, db: AsyncSession = Depends(get_db)):
    """Find grouping/class/cf_line by management name (L3 node)."""
    result = await db.execute(
        select(CategoryNode).where(
            CategoryNode.level == 3, CategoryNode.name == management_name
        )
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Category not found")

    class_name = None
    grouping = None

    if node.parent_id:
        res = await db.execute(select(CategoryNode).where(CategoryNode.id == node.parent_id))
        class_node = res.scalar_one_or_none()
        if class_node:
            class_name = class_node.name
            if class_node.parent_id:
                res2 = await db.execute(select(CategoryNode).where(CategoryNode.id == class_node.parent_id))
                grouping_node = res2.scalar_one_or_none()
                if grouping_node:
                    grouping = grouping_node.name

    return CategoryLookupResponse(
        management=node.name,
        class_name=class_name,
        grouping=grouping,
        cf_line=node.cf_line,
    )


@router.post("", response_model=CategoryNodeResponse)
async def create_category(data: CategoryNodeCreate, db: AsyncSession = Depends(get_db)):
    node = CategoryNode(**data.model_dump())
    db.add(node)
    await db.flush()
    return CategoryNodeResponse.model_validate(node)


@router.put("/{node_id}", response_model=CategoryNodeResponse)
async def update_category(
    node_id: int, data: CategoryNodeUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CategoryNode).where(CategoryNode.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Category not found")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(node, k, v)

    return CategoryNodeResponse.model_validate(node)


@router.delete("/{node_id}")
async def delete_category(node_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CategoryNode).where(CategoryNode.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Category not found")

    await db.delete(node)
    return {"deleted": True}
