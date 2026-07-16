/**
 * 社交互动相关类型定义（对应后端 app/schemas/social.py）
 */

/** 收藏目标类型 */
export type FavoriteTargetType = 'scenic_spot' | 'hotel' | 'restaurant'

/** 收藏 */
export interface FavoriteCreate {
  target_type: FavoriteTargetType
  target_id: number
}

export interface FavoriteResponse {
  id: number
  user_id: number
  target_type: string
  target_id: number
  created_at: string
}

/** 评论目标类型 */
export type ReviewTargetType = 'scenic_spot' | 'hotel' | 'restaurant'

/** 评论 */
export interface ReviewCreate {
  target_type: ReviewTargetType
  target_id: number
  content: string
  score?: number
}

export interface ReviewResponse {
  id: number
  user_id: number
  target_type: string
  target_id: number
  content: string
  score: number | null
  created_at: string
  updated_at: string
}
