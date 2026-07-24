/**
 * 统一旅行资源类型定义
 *
 * 本文件是项目中所有资源类型相关定义的唯一来源。
 * 其他类型文件 (plan.ts / social.ts / transit.ts / travel.ts) 均应从此处导入基础类型。
 */

// ==================== 资源类型联合 ====================

/** 全量资源类型（AI 计划 + 资源详情 + Transit 端点 + 元数据） */
export type TravelResourceType =
  | 'scenic_spot'
  | 'restaurant'
  | 'hotel'
  | 'entertainment'
  | 'shopping_mall'
  | 'general_activity'

/** 可导航资源类型（排除 general_activity：它有数据库记录、有详情页、可作为 Transit 端点） */
export type NavigableResourceType = Exclude<TravelResourceType, 'general_activity'>

/** 社交目标类型（收藏 + 评论）—— 当前完整支持五类可导航资源 */
export type SocialTargetType = NavigableResourceType

/** 规范化后的资源类型：已知类型 或 未知兜底 */
export type NormalizedResourceType = TravelResourceType | 'unknown'

// ==================== 类型守卫 ====================

const TRAVEL_RESOURCE_VALUES: ReadonlySet<string> = new Set<TravelResourceType>([
  'scenic_spot',
  'restaurant',
  'hotel',
  'entertainment',
  'shopping_mall',
  'general_activity',
])

/** 判断给定值是否为合法的 TravelResourceType */
export function isTravelResourceType(value: unknown): value is TravelResourceType {
  return typeof value === 'string' && TRAVEL_RESOURCE_VALUES.has(value)
}

const NAVIGABLE_RESOURCE_VALUES: ReadonlySet<string> = new Set<NavigableResourceType>([
  'scenic_spot',
  'restaurant',
  'hotel',
  'entertainment',
  'shopping_mall',
])

/** 判断给定值是否为可导航资源类型（排除 general_activity） */
export function isNavigableResourceType(value: unknown): value is NavigableResourceType {
  return typeof value === 'string' && NAVIGABLE_RESOURCE_VALUES.has(value)
}

// ==================== 展示元数据 ====================

/** 资源类型的最小展示元数据（仅包含纯展示信息，不包含 API URL / 路由 / 功能标记） */
export interface ResourceTypeMeta {
  type: TravelResourceType
  label: string
}

/** 六类资源的展示元数据映射表 */
export const RESOURCE_TYPE_META: Record<TravelResourceType, ResourceTypeMeta> = {
  scenic_spot:     { type: 'scenic_spot',     label: '景点' },
  restaurant:      { type: 'restaurant',      label: '餐厅' },
  hotel:           { type: 'hotel',           label: '酒店' },
  entertainment:   { type: 'entertainment',   label: '娱乐' },
  shopping_mall:   { type: 'shopping_mall',   label: '商场' },
  general_activity:{ type: 'general_activity',label: '活动' },
}

// ==================== 工具函数 ====================

/**
 * 获取资源类型的中文标签
 *
 * @param type 规范化后的资源类型
 * @param rawType 原始字符串（当 type === 'unknown' 时作为附加信息）
 * @returns 中文标签，保证非空
 */
export function getResourceTypeLabel(
  type: NormalizedResourceType,
  rawType?: string | null,
): string {
  if (type !== 'unknown') {
    return RESOURCE_TYPE_META[type].label
  }
  // 兜底：优先使用原始字符串截断，否则用通用标签
  if (rawType && rawType.trim()) {
    const trimmed = rawType.trim()
    return trimmed.length > 20 ? trimmed.slice(0, 20) + '…' : trimmed
  }
  return '其他活动'
}
