/**
 * PlanJSON 类型体系 — AI 旅行计划的结构化数据类型
 *
 * 本文件定义：
 * - AI 生成的计划 JSON 的原始结构 (StructuredTravelPlan)
 * - 运行时规范化后的安全类型 (NormalizedStructuredTravelPlan)
 * - 规范化过程中的警告模型 (NormalizeWarning)
 * - 规范化结果包装 (NormalizeResult)
 *
 * 数据库 TravelPlan 记录继续保留在 types/travel.ts 中。
 */

import type { NormalizedResourceType } from './resource'

// ==================== 地点坐标绑定类型（P5） ====================

/**
 * 地点坐标匹配状态
 *
 * - `matched`   — 后端成功匹配到平台资源，坐标可信
 * - `not_found` — 后端未匹配到对应地点，不应作为精确坐标使用
 * - `ambiguous` — 存在多个可能匹配，不确定具体地点
 * - `null`      — 未执行匹配（历史计划或新字段缺失）
 *
 * 兼容性：后端未来可能增加新枚举值，前端对未知值降级为 null。
 */
export type LocationMatchStatus =
  | 'matched'
  | 'not_found'
  | 'ambiguous'
  | null

/**
 * 地点坐标匹配来源
 *
 * - `resource_database` — 从平台资源数据库中匹配
 * - `external_poi`      — 从外部 POI 服务匹配（如高德）
 * - `manual`            — 人工标注
 * - `none`              — 无匹配来源
 * - `null`              — 未设置（历史兼容）
 */
export type LocationMatchSource =
  | 'resource_database'
  | 'external_poi'
  | 'manual'
  | 'none'
  | null

// ==================== Schema 版本 ====================

/** 已知的 PlanJSON Schema 版本 */
export type KnownPlanSchemaVersion = '1.0' | '1.1'

/** PlanJSON Schema 版本 — 兼容未来未知版本 */
export type PlanSchemaVersion = KnownPlanSchemaVersion | (string & {})

// ==================== Normalize 警告模型 ====================

/** 规范化过程中的单条警告 */
export interface NormalizeWarning {
  /** 字段路径，如 "itinerary[0].items[2].resource_type" */
  path: string
  /** 警告代码，如 "UNKNOWN_RESOURCE_TYPE" */
  code: string
  /** 人类可读描述 */
  message: string
  /** 原始值（可选，供调试） */
  rawValue?: unknown
}

/** 规范化结果包装 */
export interface NormalizeResult<T> {
  /** 规范化后的安全数据；为 null 表示原始输入无法恢复 */
  data: T | null
  /** 规范化过程中收集的非致命警告 */
  warnings: NormalizeWarning[]
  /** 传入的原始顶层数据引用（不深拷贝，仅用于调试） */
  raw: unknown
}

// ==================== 标准化旅行计划类型 ====================

/** 目的地信息 */
export interface PlanDestination {
  /** 数据库城市 ID；历史字符串形式的目的地无 city_id */
  city_id: number | null
  name: string
  province: string
  /** 城市中心纬度；用于地图搜索的默认城市范围 */
  latitude: number | null
  /** 城市中心经度 */
  longitude: number | null
}

/** 预算明细 */
export interface PlanBudgetBreakdown {
  tickets: number | null
  food: number | null
  lodging: number | null
  transport: number | null
  other: number | null
}

/** 预算信息 */
export interface PlanBudget {
  currency: string
  requested_total: number | null
  estimated_total: number | null
  breakdown: PlanBudgetBreakdown
}

/** 单日行程 */
export interface PlanDay {
  day: number
  theme: string
  summary: string | null
  weather_note: string | null
  items: PlanTimelineItem[]
  meals: PlanMeal[]
  hotel: PlanHotel | null
  daily_estimated_cost: number | null
}

/** 行程项目 */
export interface PlanTimelineItem {
  period: string
  start_time: string | null
  end_time: string | null

  /** 规范化后的资源类型；未知时为 'unknown' */
  resource_type: NormalizedResourceType
  /** 原始 resource_type 字符串（未知类型时保留，供调试和标签显示） */
  raw_resource_type: string | null
  resource_id: number | null

  name: string
  address: string | null
  duration_minutes: number | null
  estimated_cost: number | null
  reason: string | null
  transport_to_next: string | null

  /** 纬度（GCJ-02）；历史计划可能为 null */
  latitude: number | null
  /** 经度（GCJ-02）；历史计划可能为 null */
  longitude: number | null
  /** 所在城市名 */
  city: string | null
  /** 所在区县名 */
  district: string | null
  /** 高德 POI ID */
  poi_id: string | null
  /** 坐标系标识，如 "GCJ-02"；缺失时前端不假定坐标系 */
  coordinate_system: string | null
  /** 坐标匹配状态（P5）；历史计划为 null */
  location_match_status: LocationMatchStatus
  /** 坐标匹配来源（P5）；历史计划为 null */
  location_match_source: LocationMatchSource
}

/** 用餐信息 */
export interface PlanMeal {
  period: string
  /** 规范化后的资源类型；未知时为 'unknown' */
  resource_type: NormalizedResourceType
  /** 原始 resource_type 字符串 */
  raw_resource_type: string | null
  resource_id: number | null
  name: string
  estimated_cost: number | null

  /** 纬度（GCJ-02）；历史计划可能为 null */
  latitude: number | null
  /** 经度（GCJ-02）；历史计划可能为 null */
  longitude: number | null
  /** 所在城市名 */
  city: string | null
  /** 坐标系标识（P5）；历史计划为 null */
  coordinate_system: string | null
  /** 坐标匹配状态（P5）；历史计划为 null */
  location_match_status: LocationMatchStatus
  /** 坐标匹配来源（P5）；历史计划为 null */
  location_match_source: LocationMatchSource
}

/** 住宿信息 */
export interface PlanHotel {
  /** 规范化后的资源类型；未知时为 'unknown' */
  resource_type: NormalizedResourceType
  /** 原始 resource_type 字符串 */
  raw_resource_type: string | null
  resource_id: number | null
  name: string
  address: string | null
  estimated_cost: number | null

  /** 纬度（GCJ-02）；历史计划可能为 null */
  latitude: number | null
  /** 经度（GCJ-02）；历史计划可能为 null */
  longitude: number | null
  /** 所在城市名 */
  city: string | null
  /** 坐标系标识（P5）；历史计划为 null */
  coordinate_system: string | null
  /** 坐标匹配状态（P5）；历史计划为 null */
  location_match_status: LocationMatchStatus
  /** 坐标匹配来源（P5）；历史计划为 null */
  location_match_source: LocationMatchSource
}

/** 规范化后的完整结构化旅行计划 */
export interface NormalizedStructuredTravelPlan {
  schema_version: PlanSchemaVersion
  title: string
  destination: PlanDestination
  days: number
  travelers: number
  summary: string | null
  budget: PlanBudget
  itinerary: PlanDay[]
  tips: string[]
  assumptions: string[]
}
