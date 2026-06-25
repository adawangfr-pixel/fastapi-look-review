"""人工审核接口与标签更新接口。

按状态机校验流转合法性后更新审核状态；并提供更新商品标签的接口
以支持前端「改标签」操作。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    ACTION_TO_STATUS,
    Product,
    ProductTag,
    ReviewStatus,
    Tag,
    can_transition,
)

router = APIRouter(tags=["review"])


class ReviewAction(BaseModel):
    """审核请求体。"""

    action: str  # approve / reject / resubmit
    reviewer: str | None = None
    note: str | None = None


class TagsUpdate(BaseModel):
    """更新标签请求体：直接传入完整标签名称列表（覆盖式更新）。"""

    tags: list[str]


def _review_endpoint(
    sku: str, payload: ReviewAction, session: Session
) -> dict:
    """审核流转的共用逻辑，供 POST 与 PATCH 复用。"""
    review = session.exec(
        select(ReviewStatus).where(ReviewStatus.sku == sku)
    ).first()
    if review is None:
        raise HTTPException(status_code=404, detail=f"未找到审核记录：{sku}")

    target = ACTION_TO_STATUS.get(payload.action)
    if target is None:
        raise HTTPException(
            status_code=400,
            detail=f"非法 action：{payload.action}（应为 approve/reject/resubmit）",
        )

    # 状态机校验
    if not can_transition(review.status, target):
        raise HTTPException(
            status_code=400,
            detail=f"非法状态流转：{review.status} -> {target}",
        )

    review.status = target
    review.reviewer = payload.reviewer
    review.reviewed_at = datetime.utcnow()
    review.note = payload.note
    session.add(review)
    session.commit()
    session.refresh(review)

    return {
        "ok": True,
        "sku": sku,
        "status": review.status,
        "reviewer": review.reviewer,
        "reviewed_at": review.reviewed_at,
        "note": review.note,
    }


@router.post("/review/{sku}")
def review_product_post(
    sku: str,
    payload: ReviewAction,
    session: Session = Depends(get_session),
):
    """对某商品执行审核动作（POST）。"""
    return _review_endpoint(sku, payload, session)


@router.patch("/review/{sku}")
def review_product_patch(
    sku: str,
    payload: ReviewAction,
    session: Session = Depends(get_session),
):
    """对某商品执行审核动作（PATCH，与 POST 等价）。"""
    return _review_endpoint(sku, payload, session)


@router.put("/review/{sku}/tags")
def update_tags(
    sku: str,
    payload: TagsUpdate,
    session: Session = Depends(get_session),
):
    """覆盖式更新某商品的标签，支持前端「改标签」操作。"""
    product = session.get(Product, sku)
    if product is None:
        raise HTTPException(status_code=404, detail=f"商品不存在：{sku}")

    # 1. 删除该商品已有的标签关联
    existing_links = session.exec(
        select(ProductTag).where(ProductTag.product_sku == sku)
    ).all()
    for link in existing_links:
        session.delete(link)
    session.commit()

    # 2. 逐个处理新标签：标签不存在则创建，再建立关联
    for raw in payload.tags:
        tag_name = raw.strip()
        if not tag_name:
            continue
        tag = session.exec(select(Tag).where(Tag.name == tag_name)).first()
        if tag is None:
            tag = Tag(name=tag_name)
            session.add(tag)
            session.commit()
            session.refresh(tag)
        link = ProductTag(product_sku=sku, tag_id=tag.id)
        session.add(link)
    session.commit()

    return {"ok": True, "sku": sku, "tags": payload.tags}
