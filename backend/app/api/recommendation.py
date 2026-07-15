"""收藏 & 评论 API"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.social import (
    FavoriteCreate, FavoriteResponse,
    ReviewCreate, ReviewUpdate, ReviewResponse,
)
from app.services import recommendation_service
from app.utils.response import success

router = APIRouter(prefix="/social", tags=["收藏 & 评论"])


# ==================== Favorite ====================

@router.get("/favorites", response_model=dict)
def list_favorites(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的收藏列表"""
    favorites = recommendation_service.get_favorites_by_user(db, current_user.id, skip=skip, limit=limit)
    return success(data=[FavoriteResponse.model_validate(f).model_dump() for f in favorites])


@router.post("/favorites", response_model=dict)
def add_favorite(data: FavoriteCreate, current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """添加收藏"""
    # 检查是否已收藏
    if recommendation_service.is_favorited(db, current_user.id, data.target_type, data.target_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已收藏，请勿重复收藏")
    favorite = recommendation_service.create_favorite(
        db, current_user.id, data.target_type, data.target_id
    )
    return success(data=FavoriteResponse.model_validate(favorite).model_dump(), message="收藏成功")


@router.delete("/favorites/{favorite_id}", response_model=dict)
def remove_favorite(favorite_id: int, current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """取消收藏"""
    favorite = recommendation_service.get_favorite_by_id(db, favorite_id)
    if favorite is None or favorite.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="收藏不存在")
    recommendation_service.delete_favorite(db, favorite)
    return success(message="已取消收藏")


# ==================== Review ====================

@router.get("/reviews", response_model=dict)
def list_reviews(
    target_type: str = Query(..., description="目标类型: scenic_spot/hotel/restaurant"),
    target_id: int = Query(..., description="目标ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """某目标（景点/酒店/餐厅）的评论列表"""
    reviews = recommendation_service.get_reviews_by_target(
        db, target_type, target_id, skip=skip, limit=limit
    )
    return success(data=[ReviewResponse.model_validate(r).model_dump() for r in reviews])


@router.post("/reviews", response_model=dict)
def create_review(data: ReviewCreate, current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """发表评论"""
    review = recommendation_service.create_review(
        db, current_user.id, data.target_type, data.target_id,
        data.content, data.score,
    )
    return success(data=ReviewResponse.model_validate(review).model_dump(), message="评论成功")


@router.put("/reviews/{review_id}", response_model=dict)
def update_review(review_id: int, data: ReviewUpdate,
                  current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """编辑评论"""
    review = recommendation_service.get_review_by_id(db, review_id)
    if review is None or review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
    review = recommendation_service.update_review(db, review, **data.model_dump(exclude_unset=True))
    return success(data=ReviewResponse.model_validate(review).model_dump(), message="评论更新成功")


@router.delete("/reviews/{review_id}", response_model=dict)
def delete_review(review_id: int, current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """删除评论"""
    review = recommendation_service.get_review_by_id(db, review_id)
    if review is None or review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
    recommendation_service.delete_review(db, review)
    return success(message="评论已删除")
