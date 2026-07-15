"""收藏 & 评论 Service"""
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.favorite import Favorite
from app.models.review import Review


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


def delete_review(db: Session, review: Review) -> None:
    """删除评论"""
    db.delete(review)
    db.commit()
