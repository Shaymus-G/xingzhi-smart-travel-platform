/**
 * 旅行计划分享 API 封装
 *
 * 对应后端接口（基于 2026-07-29 OpenAPI 实际路由）：
 *   POST   /api/travel/plans/{plan_id}/shares          创建分享
 *   GET    /api/travel/plans/{plan_id}/shares          分享列表
 *   DELETE /api/travel/plans/{plan_id}/shares/{share_id} 撤销分享
 *   GET    /api/public/plan-shares/{token}              公开快照
 */
import { http } from './request'
import type { CreateShareParams } from '@/types/plan-share'
import {
  normalizeShareCreated,
  normalizeShareInfoList,
  normalizePublicSnapshot,
} from '@/types/plan-share'
import type {
  ShareCreated,
  ShareInfo,
  ShareNormalizeResult,
  PublicShareSnapshot,
} from '@/types/plan-share'

// ==================== 参数校验常量 ====================

const MIN_EXPIRES_HOURS = 1
const MAX_EXPIRES_HOURS = 720
const DEFAULT_EXPIRES_HOURS = 72

/**
 * 校验并规范创建参数
 *
 * 规则：
 *   - expiresInHours: 1-720，超出范围裁剪，默认 72
 *   - includeBudget: 默认 false
 */
function normalizeCreateParams(params?: CreateShareParams): {
  expires_in_hours: number
  include_budget: boolean
} {
  let hours = params?.expiresInHours ?? DEFAULT_EXPIRES_HOURS
  if (typeof hours !== 'number' || !Number.isFinite(hours)) {
    hours = DEFAULT_EXPIRES_HOURS
  }
  hours = Math.round(hours)
  if (hours < MIN_EXPIRES_HOURS) hours = MIN_EXPIRES_HOURS
  if (hours > MAX_EXPIRES_HOURS) hours = MAX_EXPIRES_HOURS

  const includeBudget = params?.includeBudget === true

  return { expires_in_hours: hours, include_budget: includeBudget }
}

// ==================== API 函数 ====================

/**
 * 创建旅行计划公开分享
 *
 * @param planId 计划 ID
 * @param params 可选配置（有效期、是否公开预算）
 * @returns 规范化后的创建结果
 *
 * 注意：share_token 仅在本次响应中返回，后续列表接口不包含。
 */
export async function createPlanShare(
  planId: number,
  params?: CreateShareParams,
): Promise<ShareNormalizeResult<ShareCreated>> {
  const query = normalizeCreateParams(params)

  try {
    const raw = await http.post<ShareCreated>(
      `/api/travel/plans/${planId}/shares`,
      undefined, // 无 request body
      { query: query },
    )

    return normalizeShareCreated(raw)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '创建分享失败'
    return { data: null, error: msg }
  }
}

/**
 * 获取计划的分享记录列表
 *
 * @param planId 计划 ID
 * @returns 规范化后的分享列表（包含已撤销记录；按创建时间倒序）
 */
export async function listPlanShares(
  planId: number,
): Promise<ShareNormalizeResult<ShareInfo[]>> {
  try {
    const raw = await http.get<ShareInfo[]>(
      `/api/travel/plans/${planId}/shares`,
    )

    return normalizeShareInfoList(raw)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '获取分享列表失败'
    return { data: null, error: msg }
  }
}

/**
 * 撤销分享
 *
 * @param planId  计划 ID
 * @param shareId 分享 ID（来自列表中的 share_id）
 * @returns 成功返回 undefined；失败抛出错误
 *
 * 注意：后端对已撤销的分享再次调用返回成功（幂等），前端不做特殊处理。
 */
export async function revokePlanShare(
  planId: number,
  shareId: number,
): Promise<void> {
  await http.delete<void>(
    `/api/travel/plans/${planId}/shares/${shareId}`,
  )
}

/**
 * 公开访问分享快照（无需登录）
 *
 * @param token 分享令牌（来自 share_token 或 share_url 路径最后一段）
 * @returns 规范化后的公开快照
 *
 * Token 会自动 encodeURIComponent 处理特殊字符。
 * 使用 http.publicGet() 确保不携带 Authorization header。
 * 404 / 过期 / 撤销均返回 { data: null, error: "..." }。
 */
export async function getPublicPlanShare(
  token: string,
): Promise<ShareNormalizeResult<PublicShareSnapshot>> {
  const encoded = encodeURIComponent(token)

  try {
    const raw = await http.publicGet<PublicShareSnapshot>(
      `/api/public/plan-shares/${encoded}`,
    )

    return normalizePublicSnapshot(raw)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '获取分享内容失败'
    // 404 等错误统一返回 { data: null, error }
    return { data: null, error: msg }
  }
}
