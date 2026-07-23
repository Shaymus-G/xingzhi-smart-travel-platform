/**
 * 社交互动相关类型定义（对应后端 app/schemas/social.py）
 */

import type { SocialTargetType } from './resource'

// ==================== 通用 ====================

// 重新导出统一资源类型中的社交目标类型
export type { SocialTargetType } from './resource'

/**
 * 收藏/评论的目标类型
 *
 * 当前支持五类可导航资源。
 * TargetType 保留为 SocialTargetType 的别名，确保现有 import 不中断。
 */
export type TargetType = SocialTargetType

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

/** "我的评论" 响应 — 后端 /api/social/reviews/mine 回填了目标名称和图片 */
export interface MyReview extends Review {
  target_name?: string | null
  target_image?: string | null
}
