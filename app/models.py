"""数据库表模型定义（SQLModel）。

包含商品、商品图片、标签、商品-标签关联、look 结果、审核状态六张表，
以及审核状态枚举与状态机校验逻辑。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    """商品表：以 SKU 作为主键。"""

    __tablename__ = "products"

    sku: str = Field(primary_key=True, description="商品唯一编码（主键）")
    name: str = Field(description="商品名称")
    category: str | None = Field(default=None, description="商品类目")
    brand: str | None = Field(default=None, description="品牌")
    price: float | None = Field(default=None, description="价格")
    description: str | None = Field(default=None, description="商品描述")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")


class ProductImage(SQLModel, table=True):
    """商品图片表：一个商品可以有多张图片。"""

    __tablename__ = "product_images"

    id: int | None = Field(default=None, primary_key=True)
    sku: str = Field(foreign_key="products.sku", index=True, description="所属商品 SKU")
    image_url: str = Field(description="图片本地相对路径")


class Tag(SQLModel, table=True):
    """标签表：标签名称唯一。"""

    __tablename__ = "tags"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, description="标签名称（唯一）")


class ProductTag(SQLModel, table=True):
    """商品-标签多对多关联表，复合主键 (product_sku, tag_id)。"""

    __tablename__ = "product_tags"

    product_sku: str = Field(
        foreign_key="products.sku", primary_key=True, description="商品 SKU"
    )
    tag_id: int = Field(foreign_key="tags.id", primary_key=True, description="标签 ID")


class LookResult(SQLModel, table=True):
    """look 规则产出结果表：记录每次规则运行的结论与置信度。"""

    __tablename__ = "look_results"

    id: int | None = Field(default=None, primary_key=True)
    sku: str = Field(foreign_key="products.sku", index=True, description="所属商品 SKU")
    result: str = Field(description="规则产出的 look 结果文本")
    confidence: float = Field(description="置信度（0~1）")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="生成时间")


class ReviewStatusEnum(str, Enum):
    """审核状态枚举。

    使用中文展示值，便于前端直接显示；同时作为字符串存入数据库。
    """

    PENDING = "待审核"
    APPROVED = "通过"
    REJECTED = "驳回"


class ReviewStatus(SQLModel, table=True):
    """审核状态表：每个商品对应一条当前审核状态记录。"""

    __tablename__ = "review_status"

    id: int | None = Field(default=None, primary_key=True)
    sku: str = Field(foreign_key="products.sku", index=True, description="所属商品 SKU")
    status: ReviewStatusEnum = Field(
        default=ReviewStatusEnum.PENDING, description="当前审核状态"
    )
    reviewer: str | None = Field(default=None, description="审核人")
    reviewed_at: datetime | None = Field(default=None, description="审核时间")
    note: str | None = Field(default=None, description="审核备注")


# ---------------------------------------------------------------------------
# 审核状态机
# ---------------------------------------------------------------------------

# 允许的状态流转：
#   待审核 -> 通过
#   待审核 -> 驳回
#   驳回   -> 待审核（重新提交）
ALLOWED_TRANSITIONS: dict[ReviewStatusEnum, set[ReviewStatusEnum]] = {
    ReviewStatusEnum.PENDING: {ReviewStatusEnum.APPROVED, ReviewStatusEnum.REJECTED},
    ReviewStatusEnum.REJECTED: {ReviewStatusEnum.PENDING},
    ReviewStatusEnum.APPROVED: set(),  # 通过为终态，不允许再流转
}

# 前端动作 -> 目标状态 的映射
ACTION_TO_STATUS: dict[str, ReviewStatusEnum] = {
    "approve": ReviewStatusEnum.APPROVED,
    "reject": ReviewStatusEnum.REJECTED,
    "resubmit": ReviewStatusEnum.PENDING,
}


def can_transition(current: ReviewStatusEnum, target: ReviewStatusEnum) -> bool:
    """校验从 current 状态流转到 target 状态是否合法。"""
    return target in ALLOWED_TRANSITIONS.get(current, set())
