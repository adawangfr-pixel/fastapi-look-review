"""商品列表查询接口。

分页返回商品及其图片、标签、最新 look 结果与当前审核状态。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, func, select

from app.database import get_session
from app.models import (
    LookResult,
    Product,
    ProductImage,
    ProductTag,
    ReviewStatus,
    Tag,
)

router = APIRouter(tags=["products"])


@router.get("/products")
def list_products(
    *,
    session: Session = Depends(get_session),
    offset: int = Query(default=0, ge=0, description="分页偏移量"),
    limit: int = Query(default=20, ge=1, le=100, description="每页数量"),
):
    """分页返回商品聚合信息列表与总数。"""
    total = session.exec(select(func.count()).select_from(Product)).one()

    products = session.exec(
        select(Product).order_by(Product.created_at.desc()).offset(offset).limit(limit)
    ).all()

    items = []
    for product in products:
        # 图片列表
        images = session.exec(
            select(ProductImage.image_url).where(ProductImage.sku == product.sku)
        ).all()

        # 标签列表（联表 product_tags + tags）
        tags = session.exec(
            select(Tag.name)
            .join(ProductTag, ProductTag.tag_id == Tag.id)
            .where(ProductTag.product_sku == product.sku)
        ).all()

        # 最新 look 结果
        look = session.exec(
            select(LookResult)
            .where(LookResult.sku == product.sku)
            .order_by(LookResult.created_at.desc())
        ).first()

        # 当前审核状态
        review = session.exec(
            select(ReviewStatus).where(ReviewStatus.sku == product.sku)
        ).first()

        items.append(
            {
                "sku": product.sku,
                "name": product.name,
                "category": product.category,
                "brand": product.brand,
                "price": product.price,
                "description": product.description,
                "created_at": product.created_at,
                "images": list(images),
                "tags": list(tags),
                "look_result": look.result if look else None,
                "confidence": look.confidence if look else None,
                "review_status": review.status if review else None,
                "reviewer": review.reviewer if review else None,
                "reviewed_at": review.reviewed_at if review else None,
                "note": review.note if review else None,
            }
        )

    return {"total": total, "offset": offset, "limit": limit, "items": items}
