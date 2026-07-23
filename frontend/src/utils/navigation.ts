/**
 * 统一资源详情导航工具
 *
 * 正式支持：scenic_spot / hotel / restaurant / entertainment / shopping_mall
 */

import type { TravelResourceType } from '@/types/resource'

// ==================== 支持边界 ====================

/** 当前支持查看详情的资源类型（五类数据库资源） */
export type DetailSupportedResourceType =
  | 'scenic_spot'
  | 'hotel'
  | 'restaurant'
  | 'entertainment'
  | 'shopping_mall'

const DETAIL_SUPPORTED: ReadonlySet<string> = new Set<DetailSupportedResourceType>([
  'scenic_spot',
  'hotel',
  'restaurant',
  'entertainment',
  'shopping_mall',
])

// ==================== 类型守卫 ====================

/** 正整数校验（排除 0、负数、NaN、Infinity、小数） */
export function isValidResourceId(id: unknown): id is number {
  return typeof id === 'number' && Number.isInteger(id) && id > 0
}

/** 判断是否为 Task-3 支持查看详情的资源类型 */
export function isDetailSupportedResourceType(type: unknown): type is DetailSupportedResourceType {
  return typeof type === 'string' && DETAIL_SUPPORTED.has(type)
}

// ==================== URL 构造 ====================

/**
 * 构造资源详情页 URL
 *
 * @returns URL 字符串；不支持的类型或非法 ID 返回 null
 */
export function getResourceDetailUrl(
  type: TravelResourceType | 'unknown',
  id: number | null | undefined,
): string | null {
  if (!isValidResourceId(id)) return null
  if (!isDetailSupportedResourceType(type)) return null

  if (type === 'scenic_spot') {
    return `/pages/scenic/detail?id=${id}`
  }

  // hotel / restaurant → 通用详情页
  return `/pages/resource/detail?type=${type}&id=${id}`
}

// ==================== 导航执行 ====================

/**
 * 打开资源详情页
 *
 * @returns true 表示已发起导航；false 表示参数无效（无导航发生）
 */
export function openResourceDetail(
  type: TravelResourceType | 'unknown',
  id: number | null | undefined,
): boolean {
  const url = getResourceDetailUrl(type, id)
  if (!url) return false

  uni.navigateTo({ url })
  return true
}
