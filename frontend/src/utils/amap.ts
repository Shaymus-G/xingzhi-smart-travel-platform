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
import {
  getScenicDetail,
  getHotelDetail,
  getRestaurantDetail,
  getEntertainmentDetail,
  getMallDetail,
} from '@/api/travel'
import type { ApiError } from '@/api/request'

// ==================== 类型 ====================

/** 有效的坐标对 */
export interface ValidLocation {
  latitude: number
  longitude: number
}

/** 地点信息，用于地图打开 */
export interface MapLocationInfo {
  name: string
  address: string | null
  city: string | null
  location: ValidLocation | null
}

/** 高德地图操作选项 */
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
 * App: plus.runtime.openURL → 失败降级 webUrl
 * H5: window.open → 失败降级 复制链接
 */
export function openExternalUrl(appUrl: string, webUrl: string, fallbackText: string): void {
  if (isAppEnv()) {
    // #ifdef APP-PLUS
    plus.runtime.openURL(appUrl, (err?: { code?: number; message?: string }) => {
      // 打开失败 → 降级到 Web URL
      if (err) {
        plus.runtime.openURL(webUrl, () => {
          // Web 也失败 → 复制链接
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

  // H5 / 小程序：window.open
  const win = window.open(appUrl, '_blank')
  if (!win) {
    // 弹窗被阻止 → 降级为当前页跳转
    window.location.href = webUrl
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
