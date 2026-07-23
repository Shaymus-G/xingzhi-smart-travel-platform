/**
 * 交通路径规划 API（对应后端 /api/transit/*）
 */
import { http } from './request'
import type { TransitRouteRequest, TransitRouteResult } from '@/types/transit'

/** 两点间路径规划（资源 ID 模式，后端查询坐标） */
export function getTransitRoute(params: TransitRouteRequest): Promise<TransitRouteResult> {
  const query: Record<string, unknown> = {
    from_type: params.from_type,
    from_id: params.from_id,
    to_type: params.to_type,
    to_id: params.to_id,
    method: params.method,
  }
  if (params.city) query.city = params.city

  return http.get<TransitRouteResult>('/api/transit/route', query)
}
