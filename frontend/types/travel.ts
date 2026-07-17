/**
 * 旅游资源相关类型定义（对应后端 app/schemas/）
 *
 * 注意：后端 MySQL DECIMAL 字段可能被序列化为 number 或 string，
 * 因此 score/price/latitude/longitude 等字段类型兼容 number | string。
 */

// ==================== City ====================

export interface City {
  id: number
  name: string
  province?: string | null
  country?: string | null
  description?: string | null
  cover_image?: string | null
  latitude?: number | string | null
  longitude?: number | string | null
  level?: string | null // 热门 / 普通 / 小众
}

// ==================== ScenicSpot ====================

export interface ScenicSpot {
  id: number
  city_id: number
  name: string
  description?: string | null
  address?: string | null
  category?: string | null
  score?: number | string | null
  price?: number | string | null
  open_time?: string | null
  latitude?: number | string | null
  longitude?: number | string | null
  image_url?: string | null
  tags_json?: unknown // JSON 数组或 JSON 字符串
}

// ==================== Hotel ====================

export interface Hotel {
  id: number
  city_id: number
  name: string
  description?: string | null
  address?: string | null
  price?: number | string | null
  score?: number | string | null
  open_time?: string | null
  latitude?: number | string | null
  longitude?: number | string | null
  image_url?: string | null
}

// ==================== Restaurant ====================

export interface Restaurant {
  id: number
  city_id: number
  name: string
  category?: string | null
  description?: string | null
  price_level?: string | null
  score?: number | string | null
  address?: string | null
  latitude?: number | string | null
  longitude?: number | string | null
  image_url?: string | null
}

// ==================== TravelPlan ====================

export interface TravelPlan {
  id: number
  user_id: number
  title: string
  destination: string
  days: number
  budget: number | string | null
  plan_json: Record<string, unknown> | null
  markdown: string | null
  created_at: string
  updated_at: string
}
