/**
 * 旅行计划分享工具
 *
 * 职责：
 * - 完整计划文本格式化
 * - 单日行程文本格式化
 * - 平台感知的文本分享（系统分享 → 剪贴板降级）
 * - 隐私过滤：不输出内部 ID、坐标、Token、notes
 *
 * 不依赖后端接口，纯前端格式化。
 */

import type { NormalizedStructuredTravelPlan, PlanDay, PlanTimelineItem, PlanMeal, PlanHotel } from '@/types/plan'
import type { TravelPlan } from '@/types/travel'

// ==================== 类型 ====================

export type ShareMethod = 'system' | 'web-share' | 'clipboard'

export type ShareResult =
  | { ok: true; method: ShareMethod }
  | { ok: false; reason: string }

// ==================== 格式化辅助 ====================

/** 安全格式化金额 */
function fmtCost(cost: number | null | undefined): string | null {
  if (cost === null || cost === undefined) return null
  if (!Number.isFinite(cost)) return null
  if (cost === 0) return '免费'
  return `¥${cost}`
}

/** 格式化时间段 */
function fmtTimeSlot(start: string | null, end: string | null): string | null {
  if (!start && !end) return null
  if (start && end) return `${start}-${end}`
  return start || end || null
}

/** 安全字符串 — 过滤 null/undefined/NaN/[object Object] */
function safeStr(val: unknown): string {
  if (val === null || val === undefined) return ''
  const s = String(val)
  if (s === 'null' || s === 'undefined' || s === 'NaN' || s === '[object Object]') return ''
  return s
}

/** 截断超长文本 */
function truncate(val: string, maxLen: number): string {
  return val.length > maxLen ? val.slice(0, maxLen) + '…' : val
}

// ==================== 完整计划文本 ====================

/**
 * 生成完整旅行计划的分享文本
 *
 * 纯文本格式，不含 Markdown/HTML。
 * 空字段跳过，不输出 undefined/null/NaN。
 */
export function buildFullPlanShareText(
  plan: TravelPlan,
  normalized: NormalizedStructuredTravelPlan,
): string {
  const lines: string[] = []

  // 标题
  const title = normalized.title || plan.title || `${plan.destination}旅行计划`
  lines.push(`【行知旅行计划】`)
  lines.push('')
  lines.push(title)

  // 概要信息
  const metaParts: string[] = []
  if (normalized.travelers > 1) {
    metaParts.push(`出行人数：${normalized.travelers} 人`)
  }
  const budgetVal = normalized.budget.estimated_total ?? (plan.budget ? Number(plan.budget) : null)
  if (budgetVal !== null && Number.isFinite(budgetVal)) {
    const b = fmtCost(budgetVal)
    if (b) metaParts.push(`预算：${b}`)
  }
  if (metaParts.length > 0) {
    lines.push(metaParts.join(' | '))
  }

  // 每日行程
  if (normalized.itinerary.length > 0) {
    for (const day of normalized.itinerary) {
      lines.push('')
      lines.push(formatDayBlock(day))
    }
  }

  // Tips（限制前 5 条）
  if (normalized.tips.length > 0) {
    lines.push('')
    lines.push('——')
    lines.push('旅行贴士：')
    for (const tip of normalized.tips.slice(0, 5)) {
      const t = safeStr(tip)
      if (t) lines.push(`· ${truncate(t, 120)}`)
    }
  }

  lines.push('')
  lines.push('——')
  lines.push('由"行知"智慧文旅生成')

  return lines.join('\n')
}

/** 格式化单日行程块 */
function formatDayBlock(day: PlanDay): string {
  const lines: string[] = []

  // 第 N 天｜主题
  const headerParts: string[] = [`第 ${day.day} 天`]
  if (day.theme) headerParts.push(day.theme)
  lines.push(headerParts.join('｜'))

  // 时间线
  if (day.items.length > 0) {
    for (const item of day.items) {
      const itemLines = formatTimelineItem(item)
      if (itemLines) lines.push(itemLines)
    }
  }

  // 餐饮
  if (day.meals.length > 0) {
    const mealNames: string[] = []
    for (const meal of day.meals) {
      const n = safeStr(meal.name)
      if (n) {
        const c = fmtCost(meal.estimated_cost)
        mealNames.push(c ? `${n}(${c})` : n)
      }
    }
    if (mealNames.length > 0) {
      lines.push(`🍜 ${mealNames.join('、')}`)
    }
  }

  // 住宿
  if (day.hotel) {
    const h = formatHotel(day.hotel)
    if (h) lines.push(h)
  }

  // 当日费用合计
  if (day.daily_estimated_cost !== null) {
    const d = fmtCost(day.daily_estimated_cost)
    if (d) lines.push(`本日预估：${d}`)
  }

  return lines.join('\n')
}

/** 格式化行程节点 */
function formatTimelineItem(item: PlanTimelineItem): string | null {
  const name = safeStr(item.name)
  if (!name || name === '未命名项目') return null

  const parts: string[] = []

  // 时间
  const timeSlot = fmtTimeSlot(item.start_time, item.end_time)
  if (timeSlot) parts.push(timeSlot)

  // 名称
  parts.push(name)

  const line = parts.join(' ')

  const details: string[] = []

  // 地址
  const addr = safeStr(item.address)
  if (addr) details.push(`📍 ${truncate(addr, 80)}`)

  // 费用
  const cost = fmtCost(item.estimated_cost)
  if (cost) details.push(`💰 ${cost}`)

  // 交通
  const transport = safeStr(item.transport_to_next)
  if (transport) details.push(`🚗 ${truncate(transport, 60)}`)

  if (details.length > 0) {
    return line + '\n' + details.join('\n')
  }
  return line
}

/** 格式化酒店 */
function formatHotel(hotel: PlanHotel): string | null {
  const name = safeStr(hotel.name)
  if (!name || name === '未命名住宿') return null
  const addr = safeStr(hotel.address)
  const cost = fmtCost(hotel.estimated_cost)
  const parts: string[] = ['🏨 ' + name]
  if (addr) parts.push(`📍 ${truncate(addr, 80)}`)
  if (cost) parts.push(`💰 ${cost}`)
  return parts.join('\n')
}

// ==================== 单日行程文本 ====================

/**
 * 生成单日行程分享文本
 */
export function buildDayShareText(
  day: PlanDay,
  destinationName: string,
): string {
  const lines: string[] = []

  // 标题
  const theme = day.theme || ''
  const headerParts: string[] = [`【行知｜${destinationName}第 ${day.day} 天】`]
  if (theme) lines.push(`主题：${theme}`)
  lines.unshift(headerParts[0])
  lines.push('')

  // 时间线
  if (day.items.length > 0) {
    for (const item of day.items) {
      const itemLines = formatTimelineItem(item)
      if (itemLines) lines.push(itemLines)
    }
  }

  // 餐饮
  if (day.meals.length > 0) {
    const mealNames: string[] = []
    for (const meal of day.meals) {
      const n = safeStr(meal.name)
      if (n) {
        const c = fmtCost(meal.estimated_cost)
        mealNames.push(c ? `${n}(${c})` : n)
      }
    }
    if (mealNames.length > 0) {
      lines.push('')
      lines.push(`🍜 ${mealNames.join('、')}`)
    }
  }

  // 住宿
  if (day.hotel) {
    const h = formatHotel(day.hotel)
    if (h) {
      lines.push('')
      lines.push(h)
    }
  }

  lines.push('')
  lines.push('——')
  lines.push('来自"行知"旅行计划')

  return lines.join('\n')
}

// ==================== 平台分享 ====================

/**
 * 分享文本
 *
 * 平台优先级：
 *   H5: navigator.share → uni.setClipboardData
 *   App: uni.setClipboardData（系统分享需真机验证）
 *
 * @returns ShareResult — ok:true 表示已处理，ok:false 表示完全失败
 */
export async function shareText(title: string, text: string): Promise<ShareResult> {
  // 内容为空不分享
  if (!text || !text.trim()) {
    return { ok: false, reason: '分享内容为空' }
  }

  // H5: 优先 Web Share API
  // #ifdef H5
  if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
    try {
      await navigator.share({ title, text })
      return { ok: true, method: 'web-share' }
    } catch (err: unknown) {
      // 用户取消不算失败
      if (err instanceof DOMException && err.name === 'AbortError') {
        return { ok: true, method: 'web-share' }
      }
      // 其他异常 → 降级到剪贴板
    }
  }
  // #endif

  // 剪贴板降级
  return copyShareText(text)
}

/**
 * 复制分享文本到剪贴板
 */
export function copyShareText(text: string): Promise<ShareResult> {
  return new Promise((resolve) => {
    uni.setClipboardData({
      data: text,
      success() {
        uni.showToast({ title: '行程内容已复制', icon: 'success' })
        resolve({ ok: true, method: 'clipboard' })
      },
      fail() {
        uni.showToast({ title: '复制失败，请稍后重试', icon: 'none' })
        resolve({ ok: false, reason: '剪贴板写入失败' })
      },
    })
  })
}

/**
 * 复制失败时的 Toast 提示
 */
export function showShareUnavailable(): void {
  uni.showToast({ title: '暂时无法分享，请复制行程内容', icon: 'none', duration: 2500 })
}
