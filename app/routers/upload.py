"""商品图片上传接口。

接收表单字段与图片文件，保存图片、创建/复用商品、生成 look 结果，
并初始化审核状态为「待审核」。
"""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlmodel import Session

from app.database import get_session
from app.models import Product, ProductImage, ReviewStatus, ReviewStatusEnum
from app.rules import generate_look_result

router = APIRouter(tags=["upload"])

# 图片保存目录（相对项目根目录）
UPLOAD_DIR = "uploads"


@router.post("/upload")
def upload_product(
    *,
    session: Session = Depends(get_session),
    sku: str = Form(..., description="商品 SKU"),
    name: str = Form(..., description="商品名称"),
    category: str | None = Form(default=None),
    brand: str | None = Form(default=None),
    price: float | None = Form(default=None),
    description: str | None = Form(default=None),
    file: UploadFile = File(..., description="商品图片"),
):
    """上传商品图片并触发 look 规则与审核初始化。"""
    # 1. 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 2. 保存图片，文件名加随机前缀避免冲突
    suffix = os.path.splitext(file.filename or "")[1]
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    rel_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(rel_path, "wb") as f:
        f.write(file.file.read())

    # 3. 商品不存在则插入
    product = session.get(Product, sku)
    created_product = False
    if product is None:
        product = Product(
            sku=sku,
            name=name,
            category=category,
            brand=brand,
            price=price,
            description=description,
        )
        session.add(product)
        session.commit()
        session.refresh(product)
        created_product = True

    # 4. 插入图片记录（存相对路径）
    image = ProductImage(sku=sku, image_url=rel_path)
    session.add(image)
    session.commit()
    session.refresh(image)

    # 5. 运行 look 规则并写入结果
    look = generate_look_result(session, sku)

    # 6. 若该商品尚无审核状态，则初始化为「待审核」
    existing_status = session.get(ReviewStatus, _get_status_id(session, sku))
    if existing_status is None:
        review = ReviewStatus(sku=sku, status=ReviewStatusEnum.PENDING)
        session.add(review)
        session.commit()

    return {
        "ok": True,
        "created_product": created_product,
        "sku": sku,
        "image_url": rel_path,
        "look_result": look.result,
        "confidence": look.confidence,
    }


def _get_status_id(session: Session, sku: str) -> int | None:
    """查询某 SKU 现有审核状态记录的 id（不存在返回 None）。"""
    from sqlmodel import select

    return session.exec(
        select(ReviewStatus.id).where(ReviewStatus.sku == sku)
    ).first()
