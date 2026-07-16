/**
 * 旅游资源 API 接口（对应后端 /api/travel/*）
 */
import { http } from './request'
import type {
  CityResponse,
  ScenicSpotResponse,
  HotelResponse,
  RestaurantResponse,
  TravelPlanResponse,
} from '@/types/travel'

// ==================== City ====================

/** 城市列表（支持按等级、省份筛选） */
export function getCities(params?: {
  skip?: number
  limit?: number
  level?: string
  province?: string
}) {
  return http.get<CityResponse[]>('/api/travel/cities', params as unknown as Record<string, unknown>)
}

/** 城市详情 */
export function getCityById(cityId: number) {
  return http.get<CityResponse>(`/api/travel/cities/${cityId}`)
}

// ==================== ScenicSpot ====================

/** 景点列表（支持按城市、类别筛选） */
export function getScenics(params?: {
  skip?: number
  limit?: number
  city_id?: number
  category?: string
}) {
  return http.get<ScenicSpotResponse[]>('/api/travel/scenics', params as unknown as Record<string, unknown>)
}

/** 景点详情 */
export function getScenicById(scenicId: number) {
  return http.get<ScenicSpotResponse>(`/api/travel/scenics/${scenicId}`)
}

// ==================== Hotel ====================

/** 酒店列表 */
export function getHotels(params?: { city_id?: number; skip?: number; limit?: number }) {
  return http.get<HotelResponse[]>('/api/travel/hotels', params as unknown as Record<string, unknown>)
}

/** 酒店详情 */
export function getHotelById(hotelId: number) {
  return http.get<HotelResponse>(`/api/travel/hotels/${hotelId}`)
}

// ==================== Restaurant ====================

/** 餐厅列表 */
export function getRestaurants(params?: { city_id?: number; skip?: number; limit?: number }) {
  return http.get<RestaurantResponse[]>('/api/travel/restaurants', params as unknown as Record<string, unknown>)
}

/** 餐厅详情 */
export function getRestaurantById(restaurantId: number) {
  return http.get<RestaurantResponse>(`/api/travel/restaurants/${restaurantId}`)
}

// ==================== TravelPlan ====================

/** 我的旅行计划列表 */
export function getMyPlans(params?: { skip?: number; limit?: number }) {
  return http.get<TravelPlanResponse[]>('/api/travel/plans', params as unknown as Record<string, unknown>)
}

/** 旅行计划详情 */
export function getPlanById(planId: number) {
  return http.get<TravelPlanResponse>(`/api/travel/plans/${planId}`)
}
