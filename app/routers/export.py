"""Excel 导出接口。

用 Pandas 将 products + review_status + look_results 汇总成 DataFrame，
通过 openpyxl 写入内存并以 .xlsx 附件形式返回。
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, Response
from sqlmodel import Session, select

from app.database import get_session
from app.models import LookResult, Product, ReviewStatus

router = APIRouter(tags=["export"])

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@router.get("/export")
def export_excel(session: Session = Depends(get_session)):
    """导出汇总报表为 Excel 文件。"""
    products = session.exec(select(Product)).all()

    rows = []
    for product in products:
        # 当前审核状态
        review = session.exec(
            select(ReviewStatus).where(ReviewStatus.sku == product.sku)
        ).first()

        # 最新 look 结果
        look = session.exec(
            select(LookResult)
            .where(LookResult.sku == product.sku)
            .order_by(LookResult.created_at.desc())
        ).first()

        rows.append(
            {
                "SKU": product.sku,
                "名称": product.name,
                "类目": product.category,
                "品牌": product.brand,
                "价格": product.price,
                "描述": product.description,
                "创建时间": product.created_at,
                "look结果": look.result if look else None,
                "置信度": look.confidence if look else None,
                "审核状态": review.status.value if review else None,
                "审核人": review.reviewer if review else None,
                "审核时间": review.reviewed_at if review else None,
                "审核备注": review.note if review else None,
            }
        )

    df = pd.DataFrame(rows)

    # 写入内存中的 Excel
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="report")
    buffer.seek(0)

    headers = {"Content-Disposition": "attachment; filename=report.xlsx"}
    return Response(
        content=buffer.getvalue(),
        media_type=XLSX_MEDIA_TYPE,
        headers=headers,
    )
