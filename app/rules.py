"""look 规则引擎。

这里用纯函数实现一套简单、可读的规则，根据商品信息与图片产出
look 结果文本和置信度。规则被拆成若干命名的小函数并组织成一个
规则列表，便于将来替换为配置化的规则表。
"""

from __future__ import annotations

from typing import Callable

from sqlmodel import Session, select

from app.models import LookResult, Product, ProductImage

# 单条规则的类型：输入商品与图片列表，命中返回 (结果文本, 置信度)，未命中返回 None
Rule = Callable[[Product, list[ProductImage]], tuple[str, float] | None]


def _rule_no_image(product: Product, images: list[ProductImage]) -> tuple[str, float] | None:
    """没有任何图片时，无法判断，返回低置信度的占位结果。"""
    if not images:
        return ("信息不足", 0.30)
    return None


def _rule_keyword_outfit(product: Product, images: list[ProductImage]) -> tuple[str, float] | None:
    """名称包含穿搭关键词时，判定为成套 look。"""
    keywords = ("套装", "穿搭", "look", "outfit", "搭配")
    name = (product.name or "").lower()
    if any(k.lower() in name for k in keywords):
        # 图片越多置信度越高
        confidence = min(0.95, 0.70 + 0.05 * len(images))
        return ("成套穿搭 look", confidence)
    return None


def _rule_apparel_category(product: Product, images: list[ProductImage]) -> tuple[str, float] | None:
    """服饰类目且图片较多时，判定为可用于 look 展示的单品。"""
    apparel = ("服饰", "服装", "女装", "男装", "鞋", "包", "配饰")
    category = product.category or ""
    if any(c in category for c in apparel):
        if len(images) >= 3:
            return ("服饰单品（图片充足，适合出 look）", 0.85)
        return ("服饰单品（图片偏少）", 0.60)
    return None


def _rule_rich_images(product: Product, images: list[ProductImage]) -> tuple[str, float] | None:
    """图片数量很多时，作为兜底也给出一个较可用的结论。"""
    if len(images) >= 5:
        return ("多图商品，可用于 look 展示", 0.75)
    return None


# 规则列表：按顺序匹配，命中第一个即返回。将来可替换为从配置/数据库加载。
RULES: list[Rule] = [
    _rule_no_image,
    _rule_keyword_outfit,
    _rule_apparel_category,
    _rule_rich_images,
]


def run_look_rules(product: Product, images: list[ProductImage]) -> tuple[str, float]:
    """运行规则引擎，返回 (look 结果文本, 置信度)。

    依次尝试每条规则，返回第一条命中的结果；若全部未命中，返回默认结果。
    """
    for rule in RULES:
        outcome = rule(product, images)
        if outcome is not None:
            return outcome
    # 默认兜底结果
    return ("普通商品（无明显 look 特征）", 0.50)


def generate_look_result(session: Session, sku: str) -> LookResult:
    """查询商品与其图片，运行规则，写入 look_results 表并返回结果对象。"""
    product = session.get(Product, sku)
    if product is None:
        raise ValueError(f"商品不存在：{sku}")

    images = list(session.exec(select(ProductImage).where(ProductImage.sku == sku)).all())

    result_text, confidence = run_look_rules(product, images)
    look = LookResult(sku=sku, result=result_text, confidence=confidence)
    session.add(look)
    session.commit()
    session.refresh(look)
    return look
