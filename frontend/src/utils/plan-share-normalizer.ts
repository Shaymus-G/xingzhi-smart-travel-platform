/**
 * 公开分享快照运行时规范化器
 *
 * 将公开 API 返回的任意数据安全转换为页面可用的 ViewModel。
 * 不强制将脱敏快照伪装成完整私人 TravelPlan。
 *
 * 数据通路：
 *   Public API raw → normalizeShareSnapshot → PublicShareViewModel
 */

import type { PublicShareSnapshot } from '@/types/plan-share'

// ==================== ViewModel ====================

/** 公开分享页面使用的稳定 ViewModel */
export interface PublicShareViewModel {
  title: string
  destination: string
  days: number
  budget: number | null
  hasBudget: boolean
  /** 结构化行程（已规范化）；null 表示无数据 */
  itinerary: ShareDayViewModel[] | null
  createdAt: string
  expiresAt: string
  /** plan_json 是否可用 */
  hasItinerary: boolean
}

export interface ShareDayViewModel {
  day: number
  theme: string
  items: ShareItemViewModel[]
  meals: ShareMealViewModel[]
  hotel: ShareHotelViewModel | null
}

export interface ShareItemViewModel {
  period: string
  name: string
  address: string | null
  durationMinutes: number | null
  estimatedCost: number | null
  transportToNext: string | null
}

export interface ShareMealViewModel {
  period: string
  name: string
  estimatedCost: number | null
}

export interface ShareHotelViewModel {
  name: string
  address: string | null
  estimatedCost: number | null
}

// ==================== 内部辅助 ====================

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function safeStr(v: unknown, fallback: string = ''): string {
  if (typeof v === 'string') return v
  if (typeof v === 'number' && Number.isFinite(v)) return String(v)
  return fallback
}

function safeNum(v: unknown): number | null {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  if (typeof v === 'string') {
    const n = Number(v)
    return Number.isFinite(n) ? n : null
  }
  return null
}

function safeDateStr(v: unknown): string {
  if (typeof v === 'string' && v.trim()) return v
  return ''
}

// ==================== 公开 API ====================

export interface ShareNormalizeResult {
  data: PublicShareViewModel | null
  error?: string
}

/**
 * 规范化公开分享快照为页面 ViewModel
 *
 * 兼容 plan_json 缺失、budget 为 null、destination 为 string 等情况。
 */
export function normalizeShareSnapshot(
  raw: PublicShareSnapshot,
): ShareNormalizeResult {
  // 基础字段
  const title = safeStr(raw.title, '未命名计划')
  const destination = safeStr(raw.destination, '')
  const days = safeNum(raw.days) ?? 1

  if (!destination) {
    return { data: null, error: '分享数据不完整' }
  }

  // 预算
  const budget = raw.budget !== null && raw.budget !== undefined
    ? safeNum(raw.budget)
    : null

  // 行程
  const itinerary = normalizeItinerary(raw.plan_json)

  return {
    data: {
      title,
      destination,
      days,
      budget,
      hasBudget: budget !== null,
      itinerary,
      createdAt: safeDateStr(raw.created_at),
      expiresAt: safeDateStr(raw.expires_at),
      hasItinerary: itinerary !== null && itinerary.length > 0,
    },
  }
}

/**
 * 规范化 plan_json 中的 itinerary 部分
 *
 * 不暴露 resource_id / city_id / 调试字段。
 */
function normalizeItinerary(raw: unknown): ShareDayViewModel[] | null {
  if (!isRecord(raw)) return null

  const itineraryRaw = raw.itinerary
  if (!Array.isArray(itineraryRaw) || itineraryRaw.length === 0) return null

  const days: ShareDayViewModel[] = []

  for (let di = 0; di < itineraryRaw.length; di++) {
    const dayRaw = itineraryRaw[di]
    if (!isRecord(dayRaw)) continue

    const dayNum = typeof dayRaw.day === 'number' ? dayRaw.day : di + 1

    // 行程项目（不含 resource_id）
    const items: ShareItemViewModel[] = []
    if (Array.isArray(dayRaw.items)) {
      for (const itemRaw of dayRaw.items) {
        if (!isRecord(itemRaw)) continue
        items.push({
          period: safeStr(itemRaw.period, 'morning'),
          name: safeStr(itemRaw.name, '未知项目'),
          address: itemRaw.address ? safeStr(itemRaw.address) : null,
          durationMinutes: safeNum(itemRaw.duration_minutes),
          estimatedCost: safeNum(itemRaw.estimated_cost),
          transportToNext: itemRaw.transport_to_next
            ? safeStr(itemRaw.transport_to_next)
            : null,
        })
      }
    }

    // 餐饮（不含 resource_id）
    const meals: ShareMealViewModel[] = []
    if (Array.isArray(dayRaw.meals)) {
      for (const mealRaw of dayRaw.meals) {
        if (!isRecord(mealRaw)) continue
        meals.push({
          period: safeStr(mealRaw.period, 'noon'),
          name: safeStr(mealRaw.name, '未命名用餐'),
          estimatedCost: safeNum(mealRaw.estimated_cost),
        })
      }
    }

    // 酒店（不含 resource_id）
    let hotel: ShareHotelViewModel | null = null
    if (isRecord(dayRaw.hotel)) {
      hotel = {
        name: safeStr(dayRaw.hotel.name, '未命名住宿'),
        address: dayRaw.hotel.address
          ? safeStr(dayRaw.hotel.address)
          : null,
        estimatedCost: safeNum(dayRaw.hotel.estimated_cost),
      }
    }

    days.push({
      day: dayNum,
      theme: safeStr(dayRaw.theme, ''),
      items,
      meals,
      hotel,
    })
  }

  return days.length > 0 ? days : null
}
