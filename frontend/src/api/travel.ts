/**
 * 旅游资源 API 接口（对应后端 /api/travel/*）
 */
import { http } from './request'
import type { City, ScenicSpot, Hotel, Restaurant, TravelPlan } from '@/types/travel'

/** 过滤掉 undefined / null / 空字符串的查询参数 */
function filterParams(params?: Record<string, unknown>): Record<string, unknown> | undefined {
  if (!params) return undefined
  const result: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      result[key] = value
    }
  }
  return Object.keys(result).length > 0 ? result : undefined
}

// ==================== City ====================

/** 城市列表 */
export function getCities(params?: {
  level?: string
  province?: string
  skip?: number
  limit?: number
}): Promise<City[]> {
  return http.get<City[]>('/api/travel/cities', filterParams(params as Record<string, unknown>))
}

/** 城市详情 */
export function getCityDetail(id: number): Promise<City> {
  return http.get<City>(`/api/travel/cities/${id}`)
}

// ==================== ScenicSpot ====================

/** 景点列表 */
export function getScenics(params?: {
  city_id?: number
  category?: string
  skip?: number
  limit?: number
}): Promise<ScenicSpot[]> {
  return http.get<ScenicSpot[]>('/api/travel/scenics', filterParams(params as Record<string, unknown>))
}

/** 景点详情 */
export function getScenicDetail(id: number): Promise<ScenicSpot> {
  return http.get<ScenicSpot>(`/api/travel/scenics/${id}`)
}

// ==================== Hotel ====================

/** 酒店列表 */
export function getHotels(params?: {
  city_id?: number
  skip?: number
  limit?: number
}): Promise<Hotel[]> {
  return http.get<Hotel[]>('/api/travel/hotels', filterParams(params as Record<string, unknown>))
}

/** 酒店详情 */
export function getHotelDetail(id: number): Promise<Hotel> {
  return http.get<Hotel>(`/api/travel/hotels/${id}`)
}

// ==================== Restaurant ====================

/** 餐厅列表 */
export function getRestaurants(params?: {
  city_id?: number
  skip?: number
  limit?: number
}): Promise<Restaurant[]> {
  return http.get<Restaurant[]>('/api/travel/restaurants', filterParams(params as Record<string, unknown>))
}

/** 餐厅详情 */
export function getRestaurantDetail(id: number): Promise<Restaurant> {
  return http.get<Restaurant>(`/api/travel/restaurants/${id}`)
}

// ==================== TravelPlan ====================

/** 我的旅行计划列表 */
export function getMyPlans(params?: { skip?: number; limit?: number }): Promise<TravelPlan[]> {
  return http.get<TravelPlan[]>('/api/travel/plans', filterParams(params as Record<string, unknown>))
}

/** 旅行计划详情 */
export function getPlanDetail(id: number): Promise<TravelPlan> {
  return http.get<TravelPlan>(`/api/travel/plans/${id}`)
}
