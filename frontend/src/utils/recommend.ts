/**
 * 推荐数据工具 — 纯函数集合
 *
 * 职责：
 *  - 将推荐接口原始数据标准化为页面/组件可消费的视图模型
 *  - 提供展示格式化辅助函数
 *
 * 不负责：
 *  - 图片 URL 解析（由 SafeImage / resolveImageUrl 处理）
 *  - UI 截断（由 CSS text-overflow 处理）
 *  - 请求和状态管理（由页面/组件处理）
 */

import type { NormalizedRecommendCity, RecommendCity } from '@/types/recommend'

// ==================== 标准化 ====================

/**
 * 标准化推荐城市数据
 *
 * 将推荐接口的原始字段映射为统一的视图模型。
 * - 不修改原对象，返回新对象
 * - 保留合法的 0 值（使用 ?? 而非 ||）
 * - 保留 null（区分"无值"和"0"）
 * - 不在此处拼接单位、星标或推荐文案
 * - 不在此处调用 resolveImageUrl()
 *
 * @param city 推荐接口返回的原始城市对象
 * @returns 标准化后的视图模型
 */
export function normalizeRecommendCity(
  city: RecommendCity,
): NormalizedRecommendCity {
  return {
    id: city.city_id,
    name: city.city_name,
    province: city.province ?? null,
    level: city.level ?? null,
    coverImage: city.cover_image ?? null,
    distanceKm: city.distance_km ?? null,
    score: city.score ?? null,
    reason: city.reason ?? null,
  }
}

// ==================== 展示格式化 ====================

/**
 * 格式化距离文本
 *
 *   null / undefined / NaN → ''
 *   0 ≤ 距离 < 1           → 保留一位小数，如 "0.5 km"
 *   距离 ≥ 1               → 最多保留一位小数，如 "42 km" 或 "41.9 km"
 *   负数                    → ''
 */
export function formatDistanceKm(
  distanceKm: number | null | undefined,
): string {
  if (distanceKm == null) return ''
  if (typeof distanceKm !== 'number' || !Number.isFinite(distanceKm)) return ''
  if (distanceKm < 0) return ''

  if (distanceKm < 1) {
    return distanceKm.toFixed(1) + ' km'
  }

  // ≥1：最多保留一位小数，去掉无意义的 .0
  const rounded = Math.round(distanceKm * 10) / 10
  if (rounded === Math.floor(rounded)) {
    return rounded.toFixed(0) + ' km'
  }
  return rounded.toFixed(1) + ' km'
}

/**
 * 格式化评分文本
 *
 *   null / undefined / NaN → ''
 *   合法数字                → 数字文本（保留一位小数）
 */
export function formatRecommendScore(
  score: number | null | undefined,
): string {
  if (score == null) return ''
  if (typeof score !== 'number' || !Number.isFinite(score)) return ''

  // 保留一位小数，去掉无意义的 .0
  const rounded = Math.round(score * 10) / 10
  if (rounded === Math.floor(rounded)) {
    return rounded.toFixed(0)
  }
  return rounded.toFixed(1)
}

/**
 * 标准化推荐理由文本
 *
 *   null / undefined → ''
 *   非空字符串        → trim 后返回
 */
export function normalizeRecommendReason(
  reason: string | null | undefined,
): string {
  if (reason == null) return ''
  return reason.trim()
}
