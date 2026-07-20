/**
 * 社交互动 API 接口（对应后端 /api/social/*）
 */
import { http, toBody } from './request'
import type {
  TargetType,
  Favorite,
  CreateFavoriteParams,
  Review,
  CreateReviewParams,
  UpdateReviewParams,
} from '@/types/social'

// ==================== Favorite ====================

/** 获取我的收藏列表 */
export function getFavorites(params?: { skip?: number; limit?: number }): Promise<Favorite[]> {
  return http.get<Favorite[]>('/api/social/favorites', params)
}

/** 添加收藏 */
export function addFavorite(data: CreateFavoriteParams): Promise<Favorite> {
  return http.post<Favorite>('/api/social/favorites', toBody(data))
}

/** 取消收藏 */
export function deleteFavorite(id: number): Promise<void> {
  return http.delete(`/api/social/favorites/${id}`)
}

// ==================== Review ====================

/** 获取目标评论列表 */
export function getReviews(params: {
  target_type: TargetType
  target_id: number
  skip?: number
  limit?: number
}): Promise<Review[]> {
  return http.get<Review[]>('/api/social/reviews', params)
}

/** 发表评论 */
export function createReview(data: CreateReviewParams): Promise<Review> {
  return http.post<Review>('/api/social/reviews', toBody(data))
}

/** 更新评论 */
export function updateReview(id: number, data: UpdateReviewParams): Promise<Review> {
  return http.put<Review>(`/api/social/reviews/${id}`, toBody(data))
}

/** 删除评论 */
export function deleteReview(id: number): Promise<void> {
  return http.delete(`/api/social/reviews/${id}`)
}
