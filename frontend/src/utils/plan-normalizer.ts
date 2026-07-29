/**
 * PlanJSON 运行时适配层
 *
 * 职责：将后端返回的任意 plan_json 数据安全地转换为 NormalizedStructuredTravelPlan。
 * 不抛异常 — 损坏的字段尽可能降级，收集 warnings 供开发调试。
 *
 * 不依赖第三方校验库。
 */

import type {
  NormalizedStructuredTravelPlan,
  PlanDestination,
  PlanBudget,
  PlanBudgetBreakdown,
  PlanDay,
  PlanTimelineItem,
  PlanMeal,
  PlanHotel,
  NormalizeResult,
  NormalizeWarning,
  PlanSchemaVersion,
} from '@/types/plan'

import {
  isTravelResourceType,
  type TravelResourceType,
  type NormalizedResourceType,
} from '@/types/resource'

import type { TravelPlan } from '@/types/travel'

// ==================== 内部辅助 ====================

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function warn(
  warnings: NormalizeWarning[],
  path: string,
  code: string,
  message: string,
  rawValue?: unknown,
): void {
  warnings.push({ path, code, message, rawValue })
}

// ==================== 数字规范化 ====================

function normalizeNullableNumber(
  raw: unknown,
  warnings: NormalizeWarning[],
  path: string,
  allowNegative: boolean = false,
): number | null {
  if (raw === null || raw === undefined) return null

  if (typeof raw === 'number') {
    if (!Number.isFinite(raw)) {
      warn(warnings, path, 'NON_FINITE_NUMBER', '数值为 Infinity 或 NaN', raw)
      return null
    }
    if (!allowNegative && raw < 0) {
      warn(warnings, path, 'NEGATIVE_NUMBER', '数值不应为负数', raw)
      return null
    }
    return raw
  }

  if (typeof raw === 'string') {
    const trimmed = raw.trim()
    if (trimmed === '') return null
    const parsed = Number(trimmed)
    if (!Number.isFinite(parsed)) {
      warn(warnings, path, 'UNPARSABLE_NUMBER', '无法解析为数值的字符串', raw)
      return null
    }
    if (!allowNegative && parsed < 0) {
      warn(warnings, path, 'NEGATIVE_NUMBER', '数值不应为负数', raw)
      return null
    }
    return parsed
  }

  warn(warnings, path, 'INVALID_NUMBER_TYPE', `期望数字或字符串，实际为 ${typeof raw}`, raw)
  return null
}

function normalizeNonNegativeNumber(
  raw: unknown,
  warnings: NormalizeWarning[],
  path: string,
): number | null {
  return normalizeNullableNumber(raw, warnings, path, false)
}

// ==================== 坐标规范化 ====================

/**
 * 规范化单个坐标值
 *
 * - null/undefined → null
 * - number: 检查 isFinite + 范围
 * - string: 尝试 Number() 解析后检查
 * - 其他类型 → null
 * - 不将无效值转为 0，不伪造坐标
 *
 * @param raw      原始值
 * @param warnings 警告收集
 * @param path     字段路径
 * @param min      有效范围最小值（纬度 -90，经度 -180）
 * @param max      有效范围最大值（纬度 90，经度 180）
 */
function normalizeCoordinate(
  raw: unknown,
  warnings: NormalizeWarning[],
  path: string,
  min: number,
  max: number,
): number | null {
  if (raw === null || raw === undefined) return null

  let value: number

  if (typeof raw === 'number') {
    value = raw
  } else if (typeof raw === 'string') {
    const trimmed = raw.trim()
    if (trimmed === '') return null
    value = Number(trimmed)
  } else {
    return null
  }

  if (!Number.isFinite(value)) {
    warn(warnings, path, 'NON_FINITE_COORD', '坐标为 Infinity 或 NaN', raw)
    return null
  }

  if (value < min || value > max) {
    warn(warnings, path, 'COORD_OUT_OF_RANGE', `坐标值 ${value} 超出范围 [${min}, ${max}]`, raw)
    return null
  }

  return value
}

// ==================== 字符串规范化 ====================

function normalizeString(raw: unknown, path: string, defaultVal: string = ''): string {
  if (typeof raw === 'string') return raw
  if (typeof raw === 'number' && Number.isFinite(raw)) return String(raw)
  return defaultVal
}

function normalizeNullableString(raw: unknown): string | null {
  if (typeof raw === 'string' && raw.trim() !== '') return raw
  if (raw === null || raw === undefined) return null
  return null
}

// ==================== 资源类型规范化 ====================

function normalizeResourceType(
  raw: unknown,
  warnings: NormalizeWarning[],
  path: string,
): { type: NormalizedResourceType; rawType: string | null } {
  if (typeof raw === 'string' && raw.trim() !== '') {
    const trimmed = raw.trim()
    if (isTravelResourceType(trimmed)) {
      return { type: trimmed, rawType: trimmed }
    }
    warn(warnings, path, 'UNKNOWN_RESOURCE_TYPE', `未知资源类型: "${trimmed}"`, trimmed)
    return { type: 'unknown', rawType: trimmed }
  }
  // 缺失或空字符串
  warn(warnings, path, 'MISSING_RESOURCE_TYPE', '缺少 resource_type 字段', raw)
  return { type: 'unknown', rawType: null }
}

// ==================== ID 规范化 ====================

function normalizeResourceId(
  raw: unknown,
  warnings: NormalizeWarning[],
  path: string,
): number | null {
  if (raw === null || raw === undefined) return null

  if (typeof raw === 'number') {
    if (Number.isInteger(raw) && raw > 0) return raw
    warn(warnings, path, 'INVALID_RESOURCE_ID', `resource_id 应为正整数，实际为 ${raw}`, raw)
    return null
  }

  if (typeof raw === 'string') {
    const trimmed = raw.trim()
    if (trimmed === '') return null
    const parsed = Number(trimmed)
    if (Number.isInteger(parsed) && parsed > 0) return parsed
    warn(warnings, path, 'INVALID_RESOURCE_ID', `resource_id 无法解析为正整数: "${trimmed}"`, raw)
    return null
  }

  warn(warnings, path, 'INVALID_RESOURCE_ID_TYPE', `resource_id 类型异常: ${typeof raw}`, raw)
  return null
}

// ==================== 数组规范化 ====================

function normalizeStringArray(
  raw: unknown,
  warnings: NormalizeWarning[],
  path: string,
): string[] {
  if (Array.isArray(raw)) {
    return raw
      .filter((item): item is string => typeof item === 'string' && item.trim() !== '')
  }
  if (raw !== null && raw !== undefined) {
    warn(warnings, path, 'NOT_AN_ARRAY', `期望数组，实际为 ${typeof raw}`, raw)
  }
  return []
}

// ==================== destination 规范化 ====================

function normalizeDestination(
  raw: unknown,
  warnings: NormalizeWarning[],
  path: string,
): PlanDestination {
  // 对象形式
  if (isRecord(raw)) {
    const cityId = normalizeResourceId(raw.city_id, warnings, `${path}.city_id`)
    return {
      city_id: cityId,
      name: normalizeString(raw.name, `${path}.name`, ''),
      province: normalizeString(raw.province, `${path}.province`, ''),
      latitude: normalizeCoordinate(raw.latitude, warnings, `${path}.latitude`, -90, 90),
      longitude: normalizeCoordinate(raw.longitude, warnings, `${path}.longitude`, -180, 180),
    }
  }

  // 历史字符串形式
  if (typeof raw === 'string' && raw.trim() !== '') {
    return {
      city_id: null,
      name: raw.trim(),
      province: '',
      latitude: null,
      longitude: null,
    }
  }

  warn(warnings, path, 'INVALID_DESTINATION', 'destination 格式无效', raw)
  return { city_id: null, name: '', province: '', latitude: null, longitude: null }
}

// ==================== budget 规范化 ====================

function normalizeBudgetBreakdown(
  raw: unknown,
  warnings: NormalizeWarning[],
  path: string,
): PlanBudgetBreakdown {
  if (!isRecord(raw)) {
    return { tickets: null, food: null, lodging: null, transport: null, other: null }
  }
  return {
    tickets: normalizeNonNegativeNumber(raw.tickets, warnings, `${path}.tickets`),
    food: normalizeNonNegativeNumber(raw.food, warnings, `${path}.food`),
    lodging: normalizeNonNegativeNumber(raw.lodging, warnings, `${path}.lodging`),
    transport: normalizeNonNegativeNumber(raw.transport, warnings, `${path}.transport`),
    other: normalizeNonNegativeNumber(raw.other, warnings, `${path}.other`),
  }
}

function normalizeBudget(
  raw: unknown,
  warnings: NormalizeWarning[],
  path: string,
): PlanBudget {
  if (!isRecord(raw)) {
    return {
      currency: 'CNY',
      requested_total: null,
      estimated_total: null,
      breakdown: { tickets: null, food: null, lodging: null, transport: null, other: null },
    }
  }
  return {
    currency: normalizeString(raw.currency, `${path}.currency`, 'CNY'),
    requested_total: normalizeNonNegativeNumber(raw.requested_total, warnings, `${path}.requested_total`),
    estimated_total: normalizeNonNegativeNumber(raw.estimated_total, warnings, `${path}.estimated_total`),
    breakdown: normalizeBudgetBreakdown(raw.breakdown, warnings, `${path}.breakdown`),
  }
}

// ==================== 子结构规范化 ====================

function normalizeTimelineItem(
  raw: unknown,
  warnings: NormalizeWarning[],
  path: string,
): PlanTimelineItem {
  if (!isRecord(raw)) {
    warn(warnings, path, 'NOT_AN_OBJECT', 'timeline item 不是对象，使用空占位', raw)
    return emptyTimelineItem()
  }

  const rt = normalizeResourceType(raw.resource_type, warnings, `${path}.resource_type`)

  return {
    period: normalizeString(raw.period, `${path}.period`, 'morning'),
    start_time: normalizeNullableString(raw.start_time),
    end_time: normalizeNullableString(raw.end_time),
    resource_type: rt.type,
    raw_resource_type: rt.rawType,
    resource_id: normalizeResourceId(raw.resource_id, warnings, `${path}.resource_id`),
    name: normalizeString(raw.name, `${path}.name`, '未命名项目'),
    address: normalizeNullableString(raw.address),
    duration_minutes: normalizeNullableNumber(raw.duration_minutes, warnings, `${path}.duration_minutes`),
    estimated_cost: normalizeNonNegativeNumber(raw.estimated_cost, warnings, `${path}.estimated_cost`),
    reason: normalizeNullableString(raw.reason),
    transport_to_next: normalizeNullableString(raw.transport_to_next),
    // 坐标字段 — 兼容别名 (lat/lng/lon)，允许负数（经度可为负）
    latitude: normalizeCoordinate(raw.latitude ?? raw.lat, warnings, `${path}.latitude`, -90, 90),
    longitude: normalizeCoordinate(raw.longitude ?? raw.lng ?? raw.lon, warnings, `${path}.longitude`, -180, 180),
    city: normalizeNullableString(raw.city),
    district: normalizeNullableString(raw.district),
    poi_id: normalizeNullableString(raw.poi_id),
    coordinate_system: normalizeNullableString(raw.coordinate_system),
  }
}

function normalizeMeal(
  raw: unknown,
  warnings: NormalizeWarning[],
  path: string,
): PlanMeal {
  if (!isRecord(raw)) {
    warn(warnings, path, 'NOT_AN_OBJECT', 'meal 不是对象，使用空占位', raw)
    return emptyMeal()
  }

  const rt = normalizeResourceType(raw.resource_type, warnings, `${path}.resource_type`)

  return {
    period: normalizeString(raw.period, `${path}.period`, 'noon'),
    resource_type: rt.type,
    raw_resource_type: rt.rawType,
    resource_id: normalizeResourceId(raw.resource_id, warnings, `${path}.resource_id`),
    name: normalizeString(raw.name, `${path}.name`, '未命名用餐'),
    estimated_cost: normalizeNonNegativeNumber(raw.estimated_cost, warnings, `${path}.estimated_cost`),
    latitude: normalizeCoordinate(raw.latitude ?? raw.lat, warnings, `${path}.latitude`, -90, 90),
    longitude: normalizeCoordinate(raw.longitude ?? raw.lng ?? raw.lon, warnings, `${path}.longitude`, -180, 180),
    city: normalizeNullableString(raw.city),
  }
}

function normalizeHotel(
  raw: unknown,
  warnings: NormalizeWarning[],
  path: string,
): PlanHotel | null {
  if (raw === null || raw === undefined) return null
  if (!isRecord(raw)) {
    warn(warnings, path, 'NOT_AN_OBJECT', 'hotel 不是对象，返回 null', raw)
    return null
  }

  const rt = normalizeResourceType(raw.resource_type, warnings, `${path}.resource_type`)

  return {
    resource_type: rt.type,
    raw_resource_type: rt.rawType,
    resource_id: normalizeResourceId(raw.resource_id, warnings, `${path}.resource_id`),
    name: normalizeString(raw.name, `${path}.name`, '未命名住宿'),
    address: normalizeNullableString(raw.address),
    estimated_cost: normalizeNonNegativeNumber(raw.estimated_cost, warnings, `${path}.estimated_cost`),
    latitude: normalizeCoordinate(raw.latitude ?? raw.lat, warnings, `${path}.latitude`, -90, 90),
    longitude: normalizeCoordinate(raw.longitude ?? raw.lng ?? raw.lon, warnings, `${path}.longitude`, -180, 180),
    city: normalizeNullableString(raw.city),
  }
}

function normalizeDay(
  raw: unknown,
  index: number,
  warnings: NormalizeWarning[],
  path: string,
): PlanDay {
  if (!isRecord(raw)) {
    warn(warnings, path, 'NOT_AN_OBJECT', 'day 不是对象，使用空占位', raw)
    return emptyDay(index + 1)
  }

  const items: PlanTimelineItem[] = Array.isArray(raw.items)
    ? raw.items.map((item: unknown, i: number) =>
        normalizeTimelineItem(item, warnings, `${path}.items[${i}]`),
      )
    : (
        raw.items !== null && raw.items !== undefined
          ? (warn(warnings, `${path}.items`, 'NOT_AN_ARRAY', 'items 不是数组', raw.items), [])
          : []
      )

  const meals: PlanMeal[] = Array.isArray(raw.meals)
    ? raw.meals.map((meal: unknown, i: number) =>
        normalizeMeal(meal, warnings, `${path}.meals[${i}]`),
      )
    : (
        raw.meals !== null && raw.meals !== undefined
          ? (warn(warnings, `${path}.meals`, 'NOT_AN_ARRAY', 'meals 不是数组', raw.meals), [])
          : []
      )

  return {
    day: typeof raw.day === 'number' && raw.day > 0 ? raw.day : index + 1,
    theme: normalizeString(raw.theme, `${path}.theme`, ''),
    summary: normalizeNullableString(raw.summary),
    weather_note: normalizeNullableString(raw.weather_note),
    items,
    meals,
    hotel: normalizeHotel(raw.hotel, warnings, `${path}.hotel`),
    daily_estimated_cost: normalizeNonNegativeNumber(
      raw.daily_estimated_cost, warnings, `${path}.daily_estimated_cost`,
    ),
  }
}

// ==================== 空占位工厂 ====================

function emptyTimelineItem(): PlanTimelineItem {
  return {
    period: 'morning',
    start_time: null,
    end_time: null,
    resource_type: 'unknown',
    raw_resource_type: null,
    resource_id: null,
    name: '未知项目',
    address: null,
    duration_minutes: null,
    estimated_cost: null,
    reason: null,
    transport_to_next: null,
    latitude: null,
    longitude: null,
    city: null,
    district: null,
    poi_id: null,
    coordinate_system: null,
  }
}

function emptyMeal(): PlanMeal {
  return {
    period: 'noon',
    resource_type: 'unknown',
    raw_resource_type: null,
    resource_id: null,
    name: '未知用餐',
    estimated_cost: null,
    latitude: null,
    longitude: null,
    city: null,
  }
}

function emptyDay(dayNum: number): PlanDay {
  return {
    day: dayNum,
    theme: '',
    summary: null,
    weather_note: null,
    items: [],
    meals: [],
    hotel: null,
    daily_estimated_cost: null,
  }
}

// ==================== schema_version 规范化 ====================

function normalizeSchemaVersion(
  raw: unknown,
  warnings: NormalizeWarning[],
): PlanSchemaVersion {
  if (typeof raw === 'string' && raw.trim() !== '') {
    const trimmed = raw.trim()
    if (trimmed === '1.0' || trimmed === '1.1') {
      return trimmed
    }
    // 未知版本 — 保留原值，继续按最新规则渲染
    warn(warnings, '', 'UNKNOWN_SCHEMA_VERSION', `未知 schema_version: "${trimmed}"，按 1.1 规则渲染`, trimmed)
    return trimmed
  }
  // 缺失 — 默认 1.0
  warn(warnings, '', 'MISSING_SCHEMA_VERSION', '缺少 schema_version，默认 1.0', raw)
  return '1.0'
}

// ==================== 主入口 ====================

/**
 * 将任意 plan_json 原始数据规范化为 NormalizedStructuredTravelPlan。
 *
 * 不抛异常。严重损坏导致无法恢复时返回 data:null。
 *
 * @param raw plan_json 的原始值（可能为对象、JSON 字符串、null 等）
 * @returns NormalizeResult<NormalizedStructuredTravelPlan>
 */
export function normalizeStructuredTravelPlan(
  raw: unknown,
): NormalizeResult<NormalizedStructuredTravelPlan> {
  const warnings: NormalizeWarning[] = []

  // --- null / undefined ---
  if (raw === null || raw === undefined) {
    return { data: null, warnings, raw }
  }

  // --- JSON 字符串 ---
  if (typeof raw === 'string') {
    const trimmed = raw.trim()
    if (trimmed === '') {
      return { data: null, warnings, raw }
    }
    try {
      const parsed = JSON.parse(trimmed)
      if (!isRecord(parsed)) {
        warn(warnings, '', 'PLAN_JSON_TOPLEVEL_TYPE', 'plan_json 解析后不是对象', parsed)
        return { data: null, warnings, raw }
      }
      return normalizeObject(parsed, warnings, raw)
    } catch {
      warn(warnings, '', 'PLAN_JSON_PARSE_ERROR', 'plan_json 字符串 JSON 解析失败', raw)
      return { data: null, warnings, raw }
    }
  }

  // --- 对象 ---
  if (isRecord(raw)) {
    return normalizeObject(raw, warnings, raw)
  }

  // --- 其他类型 ---
  warn(warnings, '', 'PLAN_JSON_INVALID_TYPE', `plan_json 类型异常: ${typeof raw}`, raw)
  return { data: null, warnings, raw }
}

function normalizeObject(
  obj: Record<string, unknown>,
  warnings: NormalizeWarning[],
  raw: unknown,
): NormalizeResult<NormalizedStructuredTravelPlan> {
  // schema_version
  const schemaVersion = normalizeSchemaVersion(obj.schema_version, warnings)

  // destination
  const destination = normalizeDestination(obj.destination, warnings, 'destination')

  // budget
  const budget = normalizeBudget(obj.budget, warnings, 'budget')

  // itinerary
  const itineraryRaw = obj.itinerary
  let itinerary: PlanDay[]
  if (Array.isArray(itineraryRaw)) {
    itinerary = itineraryRaw.map((day: unknown, i: number) =>
      normalizeDay(day, i, warnings, `itinerary[${i}]`),
    )
  } else {
    if (itineraryRaw !== null && itineraryRaw !== undefined) {
      warn(warnings, 'itinerary', 'NOT_AN_ARRAY', 'itinerary 不是数组', itineraryRaw)
    }
    itinerary = []
  }

  // days — 优先使用字段值，缺失时从 itinerary 长度推断
  let days: number
  if (typeof obj.days === 'number' && obj.days > 0) {
    days = obj.days
  } else if (typeof obj.days === 'string') {
    const parsed = Number(obj.days)
    days = Number.isFinite(parsed) && parsed > 0 ? parsed : itinerary.length || 1
  } else {
    days = itinerary.length || 1
    if (obj.days !== null && obj.days !== undefined) {
      warn(warnings, 'days', 'INVALID_DAYS', 'days 字段无效，从 itinerary 长度推断', obj.days)
    }
  }

  // travelers
  const travelers = typeof obj.travelers === 'number' && obj.travelers > 0
    ? obj.travelers
    : 1

  const data: NormalizedStructuredTravelPlan = {
    schema_version: schemaVersion,
    title: normalizeString(obj.title, 'title', '未命名计划'),
    destination,
    days,
    travelers,
    summary: normalizeNullableString(obj.summary),
    budget,
    itinerary,
    tips: normalizeStringArray(obj.tips, warnings, 'tips'),
    assumptions: normalizeStringArray(obj.assumptions, warnings, 'assumptions'),
  }

  return { data, warnings, raw }
}

// ==================== 便捷入口：从 TravelPlan 记录规范化 ====================

/**
 * 从 API 返回的 TravelPlan 数据库记录中提取并规范化 plan_json。
 *
 * 不修改 record。不将数据库顶层字段混入结构化计划对象。
 *
 * @param record 后端返回的 TravelPlan 记录
 * @returns NormalizeResult<NormalizedStructuredTravelPlan>
 */
export function normalizeTravelPlanRecord(
  record: TravelPlan,
): NormalizeResult<NormalizedStructuredTravelPlan> {
  return normalizeStructuredTravelPlan(record.plan_json)
}
