/**
 * 旅行计划分享相关类型定义
 *
 * 基于 OpenAPI 实际响应结构，非旧交接文档假设。
 * 响应 Schema 均为 object + additionalProperties:true，无明确 Response Model，
 * 因此本文件通过 runtime normalizer 保证类型安全。
 *
 * 后端接口：
 *   POST   /api/travel/plans/{plan_id}/shares          (需认证)
 *   GET    /api/travel/plans/{plan_id}/shares          (需认证)
 *   DELETE /api/travel/plans/{plan_id}/shares/{share_id} (需认证)
 *   GET    /api/public/plan-shares/{token}              (公开)
 */

// ==================== 分享创建 ====================

/** 创建分享的参数（前端使用） */
export interface CreateShareParams {
  /** 有效期（小时），范围 1-720，默认 72 */
  expiresInHours?: number
  /** 是否公开预算，默认 false */
  includeBudget?: boolean
}

/** 后端创建分享响应中的 data 字段 */
export interface ShareCreated {
  share_id: number
  /** 分享令牌 — 仅在创建时返回，列表接口不返回 */
  share_token: string
  /** 后端返回的相对 API 路径，如 "/api/public/plan-shares/xxx" */
  share_url: string
  expires_at: string
  created_at: string
}

// ==================== 分享列表 ====================

/** 分享状态 */
export type ShareStatus = 'active' | 'revoked'

/** 列表中单条分享记录 */
export interface ShareInfo {
  share_id: number
  /** 后端返回的相对 API 路径；注意可能与创建时的 share_url 不同 */
  share_url: string
  created_at: string
  expires_at: string
  status: ShareStatus
  include_budget: boolean
}

// ==================== 公开快照 ====================

/** 公开分享接口返回的 data 字段 */
export interface PublicShareSnapshot {
  title: string
  destination: string
  days: number
  /** null 表示预算未公开 */
  budget: number | null
  /** 结构化行程数据；null 表示无 plan_json 或未包含 */
  plan_json: unknown | null
  created_at: string
  expires_at: string
}

// ==================== Runtime Normalizer ====================

/** 规范化结果 */
export interface ShareNormalizeResult<T> {
  data: T | null
  error?: string
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function safeString(v: unknown): string {
  if (typeof v === 'string') return v
  if (typeof v === 'number' && Number.isFinite(v)) return String(v)
  return ''
}

function safeNumber(v: unknown): number | null {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  if (v === null || v === undefined) return null
  return null
}

function safeBoolean(v: unknown): boolean {
  if (typeof v === 'boolean') return v
  return false
}

function safeDateString(v: unknown): string {
  if (typeof v === 'string' && v.trim() !== '') return v
  return ''
}

/** 规范化创建分享响应 */
export function normalizeShareCreated(raw: unknown): ShareNormalizeResult<ShareCreated> {
  if (!isRecord(raw)) {
    return { data: null, error: '创建分享响应格式异常' }
  }

  const shareId = safeNumber(raw.share_id)
  const shareToken = safeString(raw.share_token)
  const shareUrl = safeString(raw.share_url)
  const expiresAt = safeDateString(raw.expires_at)
  const createdAt = safeDateString(raw.created_at)

  // 必需字段检查
  if (shareId === null || !shareToken || !shareUrl) {
    return { data: null, error: '创建分享响应缺少必需字段 (share_id/share_token/share_url)' }
  }

  return {
    data: {
      share_id: shareId,
      share_token: shareToken,
      share_url: shareUrl,
      expires_at: expiresAt,
      created_at: createdAt,
    },
  }
}

/** 规范化分享列表项 */
export function normalizeShareInfo(raw: unknown): ShareNormalizeResult<ShareInfo> {
  if (!isRecord(raw)) {
    return { data: null, error: '分享记录格式异常' }
  }

  const shareId = safeNumber(raw.share_id)
  const shareUrl = safeString(raw.share_url)
  const createdAt = safeDateString(raw.created_at)
  const expiresAt = safeDateString(raw.expires_at)
  const statusRaw = safeString(raw.status)
  const includeBudget = safeBoolean(raw.include_budget)

  if (shareId === null) {
    return { data: null, error: '分享记录缺少 share_id' }
  }

  const status: ShareStatus = (statusRaw === 'active' || statusRaw === 'revoked')
    ? statusRaw
    : 'active'

  return {
    data: {
      share_id: shareId,
      share_url: shareUrl || '',
      created_at: createdAt,
      expires_at: expiresAt,
      status,
      include_budget: includeBudget,
    },
  }
}

/** 规范化分享列表 */
export function normalizeShareInfoList(raw: unknown): ShareNormalizeResult<ShareInfo[]> {
  if (!Array.isArray(raw)) {
    return { data: null, error: '分享列表格式异常：期望数组' }
  }

  const items: ShareInfo[] = []
  for (let i = 0; i < raw.length; i++) {
    const result = normalizeShareInfo(raw[i])
    if (result.data) {
      items.push(result.data)
    }
    // 单个 item 损坏不阻塞整个列表
  }

  return { data: items }
}

/** 规范化公开快照 */
export function normalizePublicSnapshot(raw: unknown): ShareNormalizeResult<PublicShareSnapshot> {
  if (!isRecord(raw)) {
    return { data: null, error: '分享快照格式异常' }
  }

  const title = safeString(raw.title)
  const destination = safeString(raw.destination)
  const days = safeNumber(raw.days)
  const budget = raw.budget !== undefined && raw.budget !== null
    ? safeNumber(raw.budget)
    : null
  const createdAt = safeDateString(raw.created_at)
  const expiresAt = safeDateString(raw.expires_at)

  if (!title || !destination || days === null || days === undefined) {
    return { data: null, error: '分享快照缺少必需字段 (title/destination/days)' }
  }

  return {
    data: {
      title,
      destination,
      days: days ?? 1,
      budget,
      plan_json: raw.plan_json ?? null,
      created_at: createdAt,
      expires_at: expiresAt,
    },
  }
}
