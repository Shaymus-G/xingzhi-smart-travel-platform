/**
 * 高德地图工具函数
 *
 * 职责：
 * - 坐标验证与标准化
 * - 高德 URI / Web URL 构造
 * - 平台感知的地图打开
 * - 资源详情延迟查询 + 缓存
 *
 * 不依赖高德 SDK，仅通过 URI Scheme / HTTPS URL 唤起高德。
 */

import type { TravelResourceType } from '@/types/resource'
import { isNavigableResourceType } from '@/types/resource'
import type { LocationMatchStatus, LocationMatchSource } from '@/types/plan'
import {
  getScenicDetail,
  getHotelDetail,
  getRestaurantDetail,
  getEntertainmentDetail,
  getMallDetail,
} from '@/api/travel'
import type { ApiError } from '@/api/request'
import { appendQueryParams } from '@/utils/query'

// ==================== 类型 ====================

/** 有效的坐标对 */
export interface ValidLocation {
  latitude: number
  longitude: number
}

/** 统一地点模型，用于单点和两点路线解析 */
export interface AmapLocation {
  name: string
  address?: string | null
  city?: string | null
  latitude?: number | string | null
  longitude?: number | string | null
  resourceType?: string | null
  resourceId?: number | null
  /** 坐标匹配状态（P5）；历史计划为 null */
  matchStatus?: LocationMatchStatus
  /** 坐标匹配来源（P5）；历史计划为 null */
  matchSource?: LocationMatchSource
  /** 坐标系标识（P5）；历史计划为 null */
  coordinateSystem?: string | null
}

/** 高德地图操作选项（单点用） */
export type MapAction = 'view' | 'navigate'

// ==================== 坐标验证 ====================

/**
 * 标准化单个坐标值
 *
 * - 自动转换 string → number
 * - 检查 isFinite
 * - 检查范围
 * - 无效返回 null（不返回 0）
 */
export function normalizeCoordinate(
  value: number | string | null | undefined,
  min: number,
  max: number,
): number | null {
  if (value === null || value === undefined) return null

  let num: number
  if (typeof value === 'number') {
    num = value
  } else if (typeof value === 'string') {
    const trimmed = value.trim()
    if (trimmed === '') return null
    num = Number(trimmed)
  } else {
    return null
  }

  if (!Number.isFinite(num)) return null
  if (num < min || num > max) return null

  return num
}

/**
 * 标准化经纬度对
 *
 * 注意：高德 URI 参数顺序为 longitude,latitude（经度在前）
 * 本函数返回的 ValidLocation 保持语义顺序（latitude, longitude），
 * 调用方在构造 URI 时负责调整参数顺序。
 */
export function normalizeLocation(
  latitude: number | string | null | undefined,
  longitude: number | string | null | undefined,
): ValidLocation | null {
  const lat = normalizeCoordinate(latitude, -90, 90)
  const lng = normalizeCoordinate(longitude, -180, 180)
  if (lat === null || lng === null) return null
  return { latitude: lat, longitude: lng }
}

// ==================== 搜索文本构建 ====================

/**
 * 构建高德搜索关键词
 *
 * 组合：城市 + 名称 + 地址，去重 + 去除空字段
 */
export function buildSearchKeyword(
  name: string,
  address: string | null,
  city: string | null,
  fallbackCity?: string | null,
): string {
  const parts: string[] = []

  // 城市
  const effectiveCity = city || fallbackCity || ''
  const cityPart = effectiveCity.trim()
  if (cityPart) {
    parts.push(cityPart)
  }

  // 名称（去重：如果名称以城市名开头，不重复加城市）
  const namePart = (name || '').trim()
  if (namePart) {
    // 如果名称已经包含城市名，移除重复的城市前缀
    if (cityPart && namePart.startsWith(cityPart)) {
      parts.push(namePart)
    } else if (cityPart && parts.length > 0) {
      parts.push(namePart)
    } else if (!cityPart) {
      parts.push(namePart)
    } else {
      // cityPart 存在但 not in parts yet
      parts.push(cityPart)
      parts.push(namePart)
    }
  }

  // 地址（去重：不过滤，直接追加）
  const addrPart = (address || '').trim()
  if (addrPart && !parts.includes(addrPart)) {
    parts.push(addrPart)
  }

  // 去重保留顺序
  const seen = new Set<string>()
  const result = parts.filter(p => {
    if (seen.has(p)) return false
    seen.add(p)
    return true
  })

  const keyword = result.join(' ').trim()
  // 限制长度防止 URL 超长
  return keyword.length > 200 ? keyword.slice(0, 200) : keyword
}

// ==================== 高德 URI 构造 ====================

/** 高德 URI 基础参数 */
const AMAP_SRC = '行知'

/**
 * 构造"查看地点"URI
 *
 * 优先 marker（精确定位），坐标缺失时降级为 search（关键词搜索）
 */
export function buildAmapViewUrl(loc: ValidLocation | null, keyword: string): string {
  if (loc) {
    // 精确 marker — 参数顺序: lng,lat
    const position = `${loc.longitude},${loc.latitude}`
    const name = encodeURIComponent(keyword.slice(0, 50))
    return `https://uri.amap.com/marker?position=${position}&name=${name}&src=${AMAP_SRC}&callnative=1`
  }
  // 降级为搜索
  const encoded = encodeURIComponent(keyword)
  return `https://uri.amap.com/search?keyword=${encoded}&src=${AMAP_SRC}&callnative=1`
}

/**
 * 构造"导航到地点"URI
 *
 * 坐标缺失时不可靠，返回 null
 */
export function buildAmapNavigationUrl(loc: ValidLocation | null, keyword: string): string | null {
  if (!loc) return null
  // 参数顺序: lng,lat,名称
  const to = `${loc.longitude},${loc.latitude},${encodeURIComponent(keyword.slice(0, 50))}`
  return `https://uri.amap.com/navigation?to=${to}&mode=car&src=${AMAP_SRC}&callnative=1`
}

/**
 * 高德 Web 降级 URL（H5 浏览器使用）
 */
export function buildAmapWebUrl(loc: ValidLocation | null, keyword: string): string {
  if (loc) {
    const position = `${loc.longitude},${loc.latitude}`
    const name = encodeURIComponent(keyword.slice(0, 50))
    return `https://uri.amap.com/marker?position=${position}&name=${name}&src=${AMAP_SRC}`
  }
  const encoded = encodeURIComponent(keyword)
  return `https://uri.amap.com/search?keyword=${encoded}&src=${AMAP_SRC}`
}

// ==================== 两点路线 ====================

/** 高德路线出行方式 */
export type AmapRouteMode = 'bus' | 'car' | 'walk' | 'ride'

/**
 * 将 TransitMethod 映射为高德路线模式
 *
 * transit → bus / driving → car / walking → walk / bicycling → ride
 * 未知方式降级为 car 并输出日志。
 */
export function mapTransitMethodToAmapMode(method: string): AmapRouteMode {
  switch (method) {
    case 'transit':   return 'bus'
    case 'driving':   return 'car'
    case 'walking':   return 'walk'
    case 'bicycling': return 'ride'
    default:
      if (import.meta.env.DEV) {
        console.warn('[amap] unknown transit method, fallback to car:', method)
      }
      return 'car'
  }
}

/**
 * 构造两点路线 navigation URL
 *
 * 高德参数顺序：from=lng,lat,name&to=lng,lat,name&mode=xxx
 * 使用 appendQueryParams 安全编码，不依赖 URLSearchParams（兼容 App 运行时）。
 */
export function buildAmapRouteUrl(
  from: ValidLocation,
  fromName: string,
  to: ValidLocation,
  toName: string,
  mode: AmapRouteMode,
): string {
  const baseUrl = 'https://uri.amap.com/navigation'
  return appendQueryParams(baseUrl, {
    from: `${from.longitude},${from.latitude},${fromName.slice(0, 50)}`,
    to: `${to.longitude},${to.latitude},${toName.slice(0, 50)}`,
    mode,
    src: AMAP_SRC,
    callnative: '1',
  })
}

/**
 * 构造两点路线 Web 降级 URL（H5 浏览器用，不带 callnative）
 */
export function buildAmapRouteWebUrl(
  from: ValidLocation,
  fromName: string,
  to: ValidLocation,
  toName: string,
  mode: AmapRouteMode,
): string {
  const baseUrl = 'https://uri.amap.com/navigation'
  return appendQueryParams(baseUrl, {
    from: `${from.longitude},${from.latitude},${fromName.slice(0, 50)}`,
    to: `${to.longitude},${to.latitude},${toName.slice(0, 50)}`,
    mode,
    src: AMAP_SRC,
  })
}

// ==================== 地点坐标解析（P5 增强） ====================

/** 坐标解析来源 */
export type CoordinateSource = 'plan_json' | 'resource_api'

/** 坐标解析失败原因 */
export type CoordinateFailReason =
  | 'NOT_FOUND'
  | 'AMBIGUOUS'
  | 'INVALID_COORDINATES'
  | 'UNSUPPORTED_COORDINATE_SYSTEM'
  | 'RESOURCE_REQUEST_FAILED'

/** 坐标解析成功结果 */
export interface CoordinateResolveOk {
  ok: true
  location: ValidLocation
  source: CoordinateSource
}

/** 坐标解析失败结果 */
export interface CoordinateResolveFail {
  ok: false
  reason: CoordinateFailReason
}

/** 坐标解析结果联合 */
export type CoordinateResolveResult = CoordinateResolveOk | CoordinateResolveFail

/**
 * 解析单个 AmapLocation 的坐标
 *
 * 三层降级 + P5 match_status 可信度判断：
 *   1. 自带坐标 (latitude/longitude) — 需经过 match_status 可信度检查
 *   2. resourceType + resourceId → 查询资源详情（not_found/ambiguous 时跳过）
 *   3. 无法取得 → null
 *
 * 复用页面级缓存，不重复查询同一资源。
 *
 * P5 规则：
 *   - matched + 合法坐标 → 直接使用 plan_json 坐标，不请求 API
 *   - matched + 无效坐标 + 有资源 ID → 允许资源详情补查
 *   - not_found → 跳过资源详情补查
 *   - ambiguous → 跳过资源详情补查
 *   - 历史计划（matchStatus 缺失）→ 保留三层降级
 */
export async function resolveAmapLocation(
  loc: AmapLocation,
): Promise<ValidLocation | null> {
  const matchStatus = loc.matchStatus ?? null
  const normType = normalizeAmapResourceType(loc.resourceType)

  if (import.meta.env.DEV) {
    console.log('[amap] resolveAmapLocation', {
      name: loc.name,
      resourceType: loc.resourceType,
      normType,
      resourceId: loc.resourceId,
      hasCoord: loc.latitude != null && loc.longitude != null,
      matchStatus,
      coordinateSystem: loc.coordinateSystem,
    })
  }

  // ===== P5 快捷路径：matched + 合法坐标 =====
  // 后端已确认位置，直接信任 plan_json 中的坐标，跳过 API 补查
  if (matchStatus === 'matched') {
    const directLoc = normalizeLocation(loc.latitude, loc.longitude)
    if (directLoc) {
      // 坐标系检查：仅 GCJ-02 或 null 视为可信
      const cs = loc.coordinateSystem ?? null
      if (cs === null || cs === 'GCJ-02') {
        if (import.meta.env.DEV) {
          console.log('[amap] using plan_json coordinates (matched + GCJ-02):', directLoc)
        }
        return directLoc
      }
      // 非 GCJ-02 坐标系：坐标虽有效，但前端不负责转换
      // 降级到资源详情补查（如果有资源 ID）
      if (import.meta.env.DEV) {
        console.warn('[amap] matched but unsupported coordinate system, will attempt resource fetch:', cs)
      }
    } else {
      // matched 但坐标无效 — 数据异常，允许资源详情补查
      if (import.meta.env.DEV) {
        console.warn('[amap] matched but coordinates invalid, will attempt resource fetch')
      }
    }
  }

  // ===== P5 禁止路径：not_found / ambiguous =====
  // 后端明确未匹配或不确定 → 不浪费请求补查，直接返回 null
  // 调用方应降级到名称搜索，不用于精确路线
  if (matchStatus === 'not_found' || matchStatus === 'ambiguous') {
    if (import.meta.env.DEV) {
      console.log('[amap] skipping resource fetch: match_status=' + matchStatus)
    }
    return null
  }

  // ===== 历史兼容路径：无 matchStatus =====
  // 历史计划或未执行坐标匹配 → 保留原有三层逻辑

  // 第一优先级：自带坐标
  if (matchStatus === null) {
    const directLoc = normalizeLocation(loc.latitude, loc.longitude)
    if (directLoc) {
      if (import.meta.env.DEV) {
        console.log('[amap] using historical plan coordinates:', directLoc)
      }
      return directLoc
    }
  }

  // 第二优先级：查询资源详情
  // not_found / ambiguous 已在上方 return，不会执行到这里
  if (
    normType &&
    loc.resourceId &&
    Number.isInteger(loc.resourceId) &&
    loc.resourceId > 0
  ) {
    if (import.meta.env.DEV) {
      console.log('[amap] fetching resource detail:', { type: normType, id: loc.resourceId })
    }
    const detail = await fetchResourceCoordinates(normType, loc.resourceId)
    if (detail) {
      const detailLoc = normalizeLocation(detail.latitude, detail.longitude)
      if (detailLoc) {
        if (import.meta.env.DEV) {
          console.log('[amap] using resource API coordinates:', detailLoc)
        }
        return detailLoc
      }
    }
  }

  if (import.meta.env.DEV) {
    console.log('[amap] resolveAmapLocation failed for:', loc.name)
  }
  return null
}

/**
 * 并行解析起点和终点坐标
 *
 * 返回 [fromLoc, toLoc]，任一为 null 表示该端解析失败。
 */
export async function resolveRouteEndpoints(
  fromLoc: AmapLocation,
  toLoc: AmapLocation,
): Promise<[ValidLocation | null, ValidLocation | null]> {
  const [from, to] = await Promise.all([
    resolveAmapLocation(fromLoc),
    resolveAmapLocation(toLoc),
  ])
  return [from, to]
}

// ==================== 平台感知打开 ====================

/** 是否在 App 环境（app-plus） */
function isAppEnv(): boolean {
  // #ifdef APP-PLUS
  return true
  // #endif
  return false
}

/**
 * 打开外部 URL
 *
 * App: plus.runtime.openURL → 失败降级 webUrl → 复制链接
 * H5: 预先打开空白窗口（保留用户手势上下文） → 异步解析后赋值 URL
 *     若预开失败（弹窗被拦截）→ 当前页跳转 webUrl
 */
export function openExternalUrl(appUrl: string, webUrl: string, fallbackText: string): void {
  if (import.meta.env.DEV) {
    console.log('[amap] openExternalUrl', { platform: isAppEnv() ? 'app' : 'h5' })
  }

  if (isAppEnv()) {
    // #ifdef APP-PLUS
    if (import.meta.env.DEV) {
      console.log('[amap] open native URI')
    }
    plus.runtime.openURL(appUrl, (err?: { code?: number; message?: string }) => {
      if (err) {
        if (import.meta.env.DEV) {
          console.log('[amap] native URI failed, fallback to web')
        }
        plus.runtime.openURL(webUrl, () => {
          if (import.meta.env.DEV) {
            console.log('[amap] web open failed, copy link')
          }
          uni.setClipboardData({
            data: webUrl,
            success: () => {
              uni.showToast({ title: '已复制地图链接，请在浏览器中打开', icon: 'none' })
            },
          })
        })
      }
    })
    // #endif
    return
  }

  // H5：当前页直接跳转 webUrl（避免异步 window.open 被浏览器拦截）
  // 不使用 await 后的 window.open，因为浏览器会拦截非用户手势触发的弹窗
  if (import.meta.env.DEV) {
    console.log('[amap] H5: navigate to web URL')
  }
  window.location.assign(webUrl)
}

/**
 * 预开空白窗口 — 在用户点击同步栈中调用，保留手势上下文
 *
 * 返回 Window 对象或 null（被拦截）。
 * 异步解析完成后调用 setOpenedWindowUrl() 赋值。
 */
export function preopenBlankWindow(): Window | null {
  // #ifdef H5
  const win = window.open('', '_blank')
  if (!win && import.meta.env.DEV) {
    console.log('[amap] preopen blank window blocked')
  }
  return win
  // #endif
  return null
}

/**
 * 向预开的空白窗口设置 URL
 */
export function setOpenedWindowUrl(win: Window | null, url: string): void {
  if (win && !win.closed) {
    try {
      win.location.href = url
    } catch {
      // 跨域或其他异常 → 降级到当前页
      window.location.assign(url)
    }
  } else {
    // 窗口已被关闭或被拦截 → 当前页跳转
    window.location.assign(url)
  }
}

/**
 * 复制地点信息到剪贴板（最终降级）
 */
export function copyLocationInfo(text: string): void {
  uni.setClipboardData({
    data: text,
    success: () => {
      uni.showToast({ title: '已复制地点信息', icon: 'success' })
    },
    fail: () => {
      uni.showToast({ title: '复制失败，请手动搜索', icon: 'none' })
    },
  })
}

// ==================== 资源类型规范化 ====================

/**
 * 将后端可能返回的资源类型变体统一映射为 amap 内部使用的标准名称
 *
 * 已知变体：
 *   scenic / scenic_spot → scenic_spot
 *   entertainments / entertainment → entertainment
 *   mall / shopping_mall → shopping_mall
 *   hotel / restaurant → 不变
 */
const RESOURCE_TYPE_ALIASES: Record<string, string> = {
  scenic: 'scenic_spot',
  entertainments: 'entertainment',
  mall: 'shopping_mall',
}

export function normalizeAmapResourceType(rawType: string | null | undefined): string | null {
  if (!rawType || typeof rawType !== 'string') return null
  const trimmed = rawType.trim()
  if (!trimmed) return null

  // 先检查别名映射
  const aliased = RESOURCE_TYPE_ALIASES[trimmed]
  if (aliased) return aliased

  // 已是标准名称
  if (isNavigableResourceType(trimmed)) return trimmed

  return null
}

// ==================== 资源详情延迟查询 ====================

/** 资源详情查询结果 */
interface ResourceDetailResult {
  latitude?: number | string | null
  longitude?: number | string | null
  address?: string | null
  city?: string | null
}

/** 页面级缓存（同一资源不重复查询） */
const resourceCache = new Map<string, ResourceDetailResult>()

/** 正在进行的查询（防重复请求） */
const pendingQueries = new Map<string, Promise<ResourceDetailResult | null>>()

/**
 * 按资源类型+ID 延迟查询详情获取坐标
 *
 * 仅查询可导航资源类型（scenic_spot/hotel/restaurant/entertainment/shopping_mall）。
 * 结果缓存在页面生命周期内，同一资源不重复请求。
 */
export async function fetchResourceCoordinates(
  resourceType: string,
  resourceId: number,
): Promise<ResourceDetailResult | null> {
  if (!isNavigableResourceType(resourceType)) return null
  if (!Number.isInteger(resourceId) || resourceId <= 0) return null

  const cacheKey = `${resourceType}:${resourceId}`

  // 命中缓存
  const cached = resourceCache.get(cacheKey)
  if (cached) return cached

  // 已有进行中的查询
  const pending = pendingQueries.get(cacheKey)
  if (pending) return pending

  const promise = doFetchResource(resourceType, resourceId)
  pendingQueries.set(cacheKey, promise)

  try {
    const result = await promise
    if (result) {
      resourceCache.set(cacheKey, result)
    }
    return result
  } finally {
    pendingQueries.delete(cacheKey)
  }
}

async function doFetchResource(
  resourceType: string,
  resourceId: number,
): Promise<ResourceDetailResult | null> {
  try {
    let detail: ResourceDetailResult | null = null

    switch (resourceType) {
      case 'scenic_spot':
        detail = await getScenicDetail(resourceId)
        break
      case 'hotel':
        detail = await getHotelDetail(resourceId)
        break
      case 'restaurant':
        detail = await getRestaurantDetail(resourceId)
        break
      case 'entertainment':
        detail = await getEntertainmentDetail(resourceId)
        break
      case 'shopping_mall':
        detail = await getMallDetail(resourceId)
        break
      default:
        return null
    }

    return detail
  } catch (err: unknown) {
    // 401 由 request.ts 统一处理，此处不重复处理
    if (import.meta.env.DEV) {
      console.warn('[amap] fetch resource detail failed:', {
        resourceType,
        resourceId,
        error: err instanceof Error ? err.message : String(err),
      })
    }
    return null
  }
}

/** 清除缓存（页面卸载时调用） */
export function clearResourceCache(): void {
  resourceCache.clear()
  pendingQueries.clear()
}
