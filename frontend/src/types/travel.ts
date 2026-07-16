/**
 * 旅游资源相关类型定义（对应后端 app/schemas/city.py, scenic.py, hotel.py, restaurant.py, travel.py）
 */

// ==================== City ====================

export interface CityResponse {
  id: number
  name: string
  province: string
  country: string
  description: string | null
  cover_image: string | null
  latitude: number | null
  longitude: number | null
  level: string // 热门 / 普通 / 小众
}

// ==================== ScenicSpot ====================

export interface ScenicSpotResponse {
  id: number
  city_id: number
  name: string
  description: string | null
  address: string | null
  category: string | null
  score: number | null
  price: number | null
  open_time: string | null
  latitude: number | null
  longitude: number | null
  image_url: string | null
  tags_json: Record<string, unknown> | null
}

// ==================== Hotel ====================

export interface HotelResponse {
  id: number
  city_id: number
  name: string
  description: string | null
  address: string | null
  price: number | null
  score: number | null
  open_time: string | null
  latitude: number | null
  longitude: number | null
  image_url: string | null
}

// ==================== Restaurant ====================

export interface RestaurantResponse {
  id: number
  city_id: number
  name: string
  category: string | null
  description: string | null
  price_level: string | null
  score: number | null
  address: string | null
  latitude: number | null
  longitude: number | null
  image_url: string | null
}

// ==================== TravelPlan ====================

export interface TravelPlanResponse {
  id: number
  user_id: number
  title: string
  destination: string
  days: number
  budget: number | null
  plan_json: Record<string, unknown> | null
  markdown: string | null
  created_at: string
  updated_at: string
}
