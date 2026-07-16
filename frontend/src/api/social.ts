/**
 * 社交互动 API 接口（对应后端 /api/social/*）
 */
import { http } from './request'
import type {
  FavoriteCreate,
  FavoriteResponse,
  ReviewCreate,
  ReviewResponse,
} from '@/types/social'

// ==================== Favorite ====================

/** 我的收藏列表 */
export function getMyFavorites(params?: { skip?: number; limit?: number }) {
  return http.get<FavoriteResponse[]>('/api/social/favorites', params as unknown as Record<string, unknown>)
}

/** 添加收藏 */
export function addFavorite(data: FavoriteCreate) {
  return http.post<FavoriteResponse>('/api/social/favorites', data as unknown as Record<string, unknown>)
}

/** 取消收藏 */
export function removeFavorite(favoriteId: number) {
  return http.delete(`/api/social/favorites/${favoriteId}`)
}

// ==================== Review ====================

/** 获取目标评论列表 */
export function getReviews(params: {
  target_type: string
  target_id: number
  skip?: number
  limit?: number
}) {
  return http.get<ReviewResponse[]>('/api/social/reviews', params as unknown as Record<string, unknown>)
}

/** 发表评论 */
export function createReview(data: ReviewCreate) {
  return http.post<ReviewResponse>('/api/social/reviews', data as unknown as Record<string, unknown>)
}

/** 更新评论 */
export function updateReview(reviewId: number, data: { content?: string; score?: number }) {
  return http.put<ReviewResponse>(`/api/social/reviews/${reviewId}`, data as unknown as Record<string, unknown>)
}

/** 删除评论 */
export function deleteReview(reviewId: number) {
  return http.delete(`/api/social/reviews/${reviewId}`)
}
