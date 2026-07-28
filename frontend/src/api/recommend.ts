/**
 * 推荐 API 接口（对应后端 /api/recommend/*）
 */
import { http } from './request'
import type {
  NearbyRecommendCity,
  SimilarRecommendCity,
  ContrastRecommendCity,
  CollaborativeRecommendCity,
} from '@/types/recommend'

// ==================== 城市详情页推荐 ====================

/**
 * 周边城市推荐
 *
 * 无需登录。
 *
 * @param cityId   当前城市 ID
 * @param radiusKm 搜索半径（km），默认 200
 * @param limit    返回数量，默认 8
 */
export function getNearbyCities(
  cityId: number,
  radiusKm = 200,
  limit = 8,
): Promise<NearbyRecommendCity[]> {
  return http.get<NearbyRecommendCity[]>('/api/recommend/nearby', {
    city_id: cityId,
    radius_km: radiusKm,
    limit,
  })
}

/**
 * 相似城市推荐
 *
 * 无需登录。
 *
 * @param cityId 当前城市 ID
 * @param limit  返回数量，默认 8
 */
export function getSimilarCities(
  cityId: number,
  limit = 8,
): Promise<SimilarRecommendCity[]> {
  return http.get<SimilarRecommendCity[]>('/api/recommend/similar', {
    city_id: cityId,
    limit,
  })
}

/**
 * 反差城市推荐
 *
 * 无需登录。
 *
 * @param cityId 当前城市 ID
 * @param limit  返回数量，默认 8
 */
export function getContrastCities(
  cityId: number,
  limit = 8,
): Promise<ContrastRecommendCity[]> {
  return http.get<ContrastRecommendCity[]>('/api/recommend/contrast', {
    city_id: cityId,
    limit,
  })
}

// ==================== 首页个性化推荐 ====================

/**
 * 协同过滤推荐（个性化"猜你喜欢"）
 *
 * 需要登录（Bearer Token）。调用层应在调用前检查登录状态，
 * 避免未登录时触发全局 401 跳转。
 *
 * Token 由 request.ts 自动注入，本函数不手动处理。
 *
 * @param limit 返回数量，默认 8
 */
export function getCollaborativeCities(
  limit = 8,
): Promise<CollaborativeRecommendCity[]> {
  return http.get<CollaborativeRecommendCity[]>('/api/recommend/collaborative', {
    limit,
  })
}
