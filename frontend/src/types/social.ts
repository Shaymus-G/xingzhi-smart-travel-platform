/**
 * 社交互动相关类型定义（对应后端 app/schemas/social.py）
 */

// ==================== 通用 ====================

export type TargetType = 'scenic_spot' | 'hotel' | 'restaurant'

// ==================== Favorite ====================

export interface Favorite {
  id: number
  user_id?: number
  target_type: TargetType
  target_id: number
  created_at?: string
  target?: unknown  // 后端可能内联返回目标详情
}

export interface CreateFavoriteParams {
  target_type: TargetType
  target_id: number
}

// ==================== Review ====================

export interface ReviewUser {
  id?: number
  username?: string
  avatar?: string | null
}

export interface Review {
  id: number
  user_id?: number
  target_type: TargetType
  target_id: number
  content: string
  score: number | string  // 后端可能返回 number 或 string
  created_at?: string
  updated_at?: string
  user?: ReviewUser | null
}

export interface CreateReviewParams {
  target_type: TargetType
  target_id: number
  content: string
  score: number
}

export interface UpdateReviewParams {
  content?: string
  score?: number
}
