/**
 * 交通路径规划类型定义
 *
 * Task-1 只定义请求基础类型。
 * 完整响应类型 (TransitRoute / TransitSegment / TransitStep) 留待 Task-6
 * 结合实际 API 联调确定。
 */

import type { NavigableResourceType } from './resource'

// ==================== 交通方式 ====================

/** 出行方式 */
export type TransitMethod =
  | 'transit'    // 公交/地铁
  | 'driving'    // 驾车
  | 'walking'    // 步行
  | 'bicycling'  // 骑行

// ==================== 端点类型 ====================

/** 交通查询的端点资源类型（同 NavigableResourceType；general_activity 不可作为端点） */
export type TransitEndpointType = NavigableResourceType

// ==================== 请求参数 ====================

/** 两点间路径规划请求参数 */
export interface TransitRouteRequest {
  /** 起点资源类型 */
  from_type: TransitEndpointType
  /** 起点资源 ID */
  from_id: number
  /** 终点资源类型 */
  to_type: TransitEndpointType
  /** 终点资源 ID */
  to_id: number
  /** 出行方式 */
  method: TransitMethod
  /** 城市名（公交模式必填，用于限定高德搜索范围） */
  city?: string
}

// ==================== 响应类型 ====================

/** 路线步骤（驾车/步行/骑行） */
export interface TransitStep {
  instruction: string
  distance: string
}

/** 公交片段 */
export interface TransitSegment {
  type: string
  name?: string | null
  instruction?: string | null
  departure?: string | null
  arrival?: string | null
  via_stops?: number | null
  distance?: string | null
  duration?: string | null
}

/** 路线公共字段 */
export interface TransitRouteCommon {
  distance: string
  duration: string
}

/** 公交路线 */
export interface TransitRouteTransit extends TransitRouteCommon {
  method: 'transit'
  cost: string | null
  walking_distance: string | null
  segments: TransitSegment[]
}

/** 驾车路线 */
export interface TransitRouteDriving extends TransitRouteCommon {
  method: 'driving'
  traffic_lights: number | null
  toll: string | null
  steps: TransitStep[]
}

/** 步行路线 */
export interface TransitRouteWalking extends TransitRouteCommon {
  method: 'walking'
  steps: TransitStep[]
}

/** 骑行路线 */
export interface TransitRouteBicycling extends TransitRouteCommon {
  method: 'bicycling'
  steps: TransitStep[]
}

/** 路线查询结果判别联合 */
export type TransitRouteResult =
  | TransitRouteTransit
  | TransitRouteDriving
  | TransitRouteWalking
  | TransitRouteBicycling
