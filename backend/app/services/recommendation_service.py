"""收藏 & 评论 Service"""
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.favorite import Favorite
from app.models.review import Review
from app.models.scenic import ScenicSpot
from app.models.hotel import Hotel
from app.models.restaurant import Restaurant
from app.models.entertainment import Entertainment
from app.models.shopping_mall import ShoppingMall


# ==================== Favorite ====================

def get_favorite_by_id(db: Session, favorite_id: int) -> Optional[Favorite]:
    return db.scalar(select(Favorite).where(Favorite.id == favorite_id))


def get_favorites_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 20) -> list[Favorite]:
    stmt = select(Favorite).where(Favorite.user_id == user_id)
    stmt = stmt.offset(skip).limit(limit).order_by(Favorite.created_at.desc())
    return list(db.scalars(stmt).all())


def is_favorited(db: Session, user_id: int, target_type: str, target_id: int) -> bool:
    """检查是否已收藏"""
    stmt = select(Favorite).where(
        Favorite.user_id == user_id,
        Favorite.target_type == target_type,
        Favorite.target_id == target_id,
    )
    return db.scalar(stmt) is not None


def create_favorite(db: Session, user_id: int, target_type: str, target_id: int) -> Favorite:
    """添加收藏"""
    favorite = Favorite(user_id=user_id, target_type=target_type, target_id=target_id)
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


def delete_favorite(db: Session, favorite: Favorite) -> None:
    """取消收藏"""
    db.delete(favorite)
    db.commit()


# ==================== Review ====================

def get_review_by_id(db: Session, review_id: int) -> Optional[Review]:
    return db.scalar(select(Review).where(Review.id == review_id))


def get_reviews_by_target(db: Session, target_type: str, target_id: int,
                          skip: int = 0, limit: int = 20) -> list[Review]:
    """获取某目标的评论列表"""
    stmt = select(Review).where(
        Review.target_type == target_type,
        Review.target_id == target_id,
    )
    stmt = stmt.offset(skip).limit(limit).order_by(Review.created_at.desc())
    return list(db.scalars(stmt).all())


def get_reviews_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 20) -> list[Review]:
    """获取某用户的评论列表"""
    stmt = select(Review).where(Review.user_id == user_id)
    stmt = stmt.offset(skip).limit(limit).order_by(Review.created_at.desc())
    return list(db.scalars(stmt).all())


def create_review(db: Session, user_id: int, target_type: str, target_id: int,
                  content: str, score: Optional[float] = None) -> Review:
    """创建评论"""
    review = Review(
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
        content=content,
        score=score,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def update_review(db: Session, review: Review, **kwargs) -> Review:
    """更新评论"""
    for key, value in kwargs.items():
        if value is not None and hasattr(review, key):
            setattr(review, key, value)
    db.commit()
    db.refresh(review)
    return review


def get_my_reviews(
    db: Session, user_id: int, skip: int = 0, limit: int = 20
) -> tuple[list[dict], int]:
    """获取当前用户的所有评论，带目标名称和图片

    Returns:
        (items, total) — items 为评论列表（含 target_name/target_image），total 为总数
    """
    # 总数
    total = db.scalar(
        select(func.count()).select_from(Review).where(Review.user_id == user_id)
    ) or 0

    # 分页查询
    reviews = db.scalars(
        select(Review)
        .where(Review.user_id == user_id)
        .order_by(Review.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    items = []
    for r in reviews:
        target_name, target_image = _resolve_target(db, r.target_type, r.target_id)
        items.append({
            "id": r.id,
            "user_id": r.user_id,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "target_name": target_name,
            "target_image": target_image,
            "content": r.content,
            "score": float(r.score) if r.score else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })

    return items, total


def _resolve_target(db: Session, target_type: str, target_id: int) -> tuple:
    """根据 target_type 联查目标名称和图片

    目标被删除时返回 ("目标已删除", None)，不抛出异常。
    """
    try:
        if target_type == "scenic_spot":
            row = db.execute(
                select(ScenicSpot.name, ScenicSpot.image_url).where(ScenicSpot.id == target_id)
            ).first()
        elif target_type == "hotel":
            row = db.execute(
                select(Hotel.name, Hotel.image_url).where(Hotel.id == target_id)
            ).first()
        elif target_type == "restaurant":
            row = db.execute(
                select(Restaurant.name, Restaurant.image_url).where(Restaurant.id == target_id)
            ).first()
        elif target_type == "entertainment":
            row = db.execute(
                select(Entertainment.name, Entertainment.image_url).where(Entertainment.id == target_id)
            ).first()
        elif target_type == "shopping_mall":
            row = db.execute(
                select(ShoppingMall.name, ShoppingMall.image_url).where(ShoppingMall.id == target_id)
            ).first()
        else:
            return ("未知目标", None)
        if row:
            return (row[0], row[1])
        return ("目标已删除", None)
    except Exception:
        return ("目标已删除", None)
