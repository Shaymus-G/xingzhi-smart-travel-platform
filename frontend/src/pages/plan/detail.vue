<script setup lang="ts">
/**
 * 旅行计划详情页面 — 使用 normalizer 安全渲染 plan_json
 */
import { ref, computed } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import NavBar from '@/components/NavBar.vue'
import { getPlanDetail, deletePlan } from '@/api/travel'
import type { TravelPlan } from '@/types/travel'
import type {
  NormalizedStructuredTravelPlan,
  NormalizeWarning,
  PlanDay,
  PlanTimelineItem,
  PlanMeal,
  PlanHotel,
} from '@/types/plan'
import { normalizeTravelPlanRecord } from '@/utils/plan-normalizer'
import { getResourceTypeLabel } from '@/types/resource'
import { getResourceDetailUrl, openResourceDetail, isValidResourceId } from '@/utils/navigation'
import type { TravelResourceType } from '@/types/resource'
import { isNavigableResourceType } from '@/types/resource'
import type { TransitEndpointType } from '@/types/transit'
import TransitRoutePanel from '@/components/TransitRoutePanel.vue'
import {
  normalizeLocation,
  buildSearchKeyword,
  buildAmapViewUrl,
  buildAmapNavigationUrl,
  buildAmapWebUrl,
  buildAmapRouteUrl,
  buildAmapRouteWebUrl,
  mapTransitMethodToAmapMode,
  openExternalUrl,
  preopenBlankWindow,
  setOpenedWindowUrl,
  copyLocationInfo,
  fetchResourceCoordinates,
  clearResourceCache,
  resolveRouteEndpoints,
} from '@/utils/amap'
import type { AmapLocation, MapAction } from '@/utils/amap'
import { buildFullPlanShareText, buildDayShareText, shareText, copyShareText } from '@/utils/plan-share'
import { createPlanShare, listPlanShares, revokePlanShare } from '@/api/plan-share'
import type { ShareInfo, ShareCreated } from '@/types/plan-share'

// ========== 错误类型 ==========
type PlanLoadError = 'invalidId' | 'notFound' | 'network' | 'unknown'

// ========== 状态 ==========
const plan = ref<TravelPlan | null>(null)
const normalizedPlan = ref<NormalizedStructuredTravelPlan | null>(null)
const isLoading = ref(true)
const planId = ref(0)
const hasFallbackMarkdown = ref(false)
const loadError = ref<PlanLoadError | null>(null)
const isDeleting = ref(false)
let _loading = false   // 并发锁
let _loadSeq = 0       // 请求序号（诊断用）

// ========== 地图入口 ==========

/** 正在查询坐标的节点 key */
const mapLoadingKeys = ref<Set<string>>(new Set())

/** 正在加载高德路线的段 key */
const routeLoadingKeys = ref<Set<string>>(new Set())

function nodeKey(kind: string, dayIndex: number, itemIndex: number): string {
  return `${kind}:${dayIndex}:${itemIndex}`
}

function routeKey(dayIndex: number, itemIndex: number): string {
  return `route:${dayIndex}:${itemIndex}`
}

/** 将 PlanTimelineItem 转为 AmapLocation */
function toAmapLocation(item: PlanTimelineItem): AmapLocation {
  return {
    name: item.name,
    address: item.address,
    city: item.city,
    latitude: item.latitude,
    longitude: item.longitude,
    resourceType: item.resource_type !== 'unknown' ? item.resource_type : null,
    resourceId: item.resource_id,
    matchStatus: item.location_match_status,
    matchSource: item.location_match_source,
    coordinateSystem: item.coordinate_system,
  }
}

/**
 * 处理 TransitRoutePanel 发出的高德路线事件
 */
async function handleOpenAmapRoute(
  fromItem: PlanTimelineItem,
  toItem: PlanTimelineItem,
  dayIndex: number,
  itemIndex: number,
  payload: { method: string },
): Promise<void> {
  const method = payload?.method || 'driving'
  const key = routeKey(dayIndex, itemIndex)

  if (import.meta.env.DEV) {
    console.log('[amap-route] parent handler entered', {
      from: fromItem.name,
      to: toItem.name,
      dayIndex,
      itemIndex,
      method,
    })
  }

  if (routeLoadingKeys.value.has(key)) return

  // 同步设置 loading（必须在任何 await 之前）
  const newSet = new Set(routeLoadingKeys.value)
  newSet.add(key)
  routeLoadingKeys.value = newSet

  // H5：在用户点击同步栈中预开空白窗口（防止浏览器拦截异步 window.open）
  // #ifdef H5
  const pendingWindow = preopenBlankWindow()
  // #endif

  try {
    if (import.meta.env.DEV) {
      console.log('[amap-route] endpoints resolving')
    }
    const fromLoc = toAmapLocation(fromItem)
    const toLoc = toAmapLocation(toItem)
    const [fromCoord, toCoord] = await resolveRouteEndpoints(fromLoc, toLoc)

    if (!routeLoadingKeys.value.has(key)) return

    if (import.meta.env.DEV) {
      console.log('[amap-route] endpoints resolved', {
        fromName: fromItem.name,
        fromOk: fromCoord !== null,
        fromSource: fromCoord ? 'valid' : 'null',
        fromResourceType: fromItem.resource_type,
        fromResourceId: fromItem.resource_id,
        toName: toItem.name,
        toOk: toCoord !== null,
        toSource: toCoord ? 'valid' : 'null',
        toResourceType: toItem.resource_type,
        toResourceId: toItem.resource_id,
      })
    }

    if (!fromCoord || !toCoord) {
      const missingName = !fromCoord ? fromItem.name : toItem.name
      // #ifdef H5
      if (pendingWindow && !pendingWindow.closed) pendingWindow.close()
      // #endif
      uni.showToast({
        title: `地点坐标不完整，暂时无法生成精确路线`,
        icon: 'none',
        duration: 3000,
      })
      return
    }

    const mode = mapTransitMethodToAmapMode(method)
    const appUrl = buildAmapRouteUrl(fromCoord, fromItem.name, toCoord, toItem.name, mode)
    const webUrl = buildAmapRouteWebUrl(fromCoord, fromItem.name, toCoord, toItem.name, mode)

    if (import.meta.env.DEV) {
      console.log('[amap-route] URL built', {
        mode,
        from: `${fromCoord.longitude},${fromCoord.latitude}`,
        to: `${toCoord.longitude},${toCoord.latitude}`,
      })
    }

    // #ifdef H5
    if (pendingWindow && !pendingWindow.closed) {
      setOpenedWindowUrl(pendingWindow, webUrl)
    } else {
      openExternalUrl(appUrl, webUrl, `${fromItem.name} → ${toItem.name}`)
    }
    // #endif
    // #ifdef APP-PLUS
    openExternalUrl(appUrl, webUrl, `${fromItem.name} → ${toItem.name}`)
    // #endif
  } catch (err: unknown) {
    if (!routeLoadingKeys.value.has(key)) return
    // #ifdef H5
    if (pendingWindow && !pendingWindow.closed) pendingWindow.close()
    // #endif
    const msg = err instanceof Error ? err.message : '路线打开失败'
    uni.showToast({ title: msg, icon: 'none', duration: 3000 })
    uni.setClipboardData({
      data: `${fromItem.name} → ${toItem.name}`,
      showToast: false,
    })
  } finally {
    const newSet2 = new Set(routeLoadingKeys.value)
    newSet2.delete(key)
    routeLoadingKeys.value = newSet2
  }
}

/** 构建地点信息对象 */
function buildLocationInfo(
  item: PlanTimelineItem | PlanMeal | PlanHotel,
): { name: string; address: string | null; city: string | null; lat: number | null; lng: number | null } {
  return {
    name: item.name,
    address: 'address' in item ? (item.address ?? null) : null,
    city: 'city' in item ? (item.city ?? null) : null,
    lat: 'latitude' in item ? (item.latitude ?? null) : null,
    lng: 'longitude' in item ? (item.longitude ?? null) : null,
  }
}

/**
 * 地图按钮点击处理
 *
 * 三层降级：
 *   1. 节点自带坐标 → 直接打开高德
 *   2. resource_type + resource_id → 延迟查询资源详情
 *   3. 名称 + 地址 + 城市 → 高德搜索
 */
async function handleOpenMap(
  item: PlanTimelineItem | PlanMeal | PlanHotel,
  dayIndex: number,
  itemIndex: number,
): Promise<void> {
  const key = nodeKey('map', dayIndex, itemIndex)
  if (mapLoadingKeys.value.has(key)) return

  const info = buildLocationInfo(item)

  // 第一优先级：节点自带坐标
  const directLoc = normalizeLocation(info.lat, info.lng)

  if (directLoc) {
    showMapActionSheet(info.name, info.address, info.city, directLoc)
    return
  }

  // 第二优先级：延迟查询资源详情
  if (
    isNavigableResourceType(item.resource_type) &&
    item.resource_id !== null &&
    item.resource_id > 0
  ) {
    const newSet = new Set(mapLoadingKeys.value)
    newSet.add(key)
    mapLoadingKeys.value = newSet

    try {
      const detail = await fetchResourceCoordinates(item.resource_type, item.resource_id)
      if (detail) {
        const loc = normalizeLocation(detail.latitude, detail.longitude)
        const detailCity = detail.city || info.city
        const detailAddr = detail.address || info.address
        showMapActionSheet(info.name, detailAddr, detailCity, loc)
        return
      }
    } catch {
      // 查询失败 → 降级到搜索
    } finally {
      const newSet2 = new Set(mapLoadingKeys.value)
      newSet2.delete(key)
      mapLoadingKeys.value = newSet2
    }
  }

  // 第三优先级：名称搜索
  const fallbackCity = info.city || normalizedPlan.value?.destination?.name || null
  showMapActionSheet(info.name, info.address, fallbackCity, null)
}

/** 显示操作菜单 */
function showMapActionSheet(
  name: string,
  address: string | null,
  city: string | null,
  loc: { latitude: number; longitude: number } | null,
): void {
  const keyword = buildSearchKeyword(name, address, city, normalizedPlan.value?.destination?.name ?? null)
  const itemList: string[] = loc
    ? ['查看地点（精确定位）', '从当前位置前往']
    : ['在高德地图中搜索此地点']

  uni.showActionSheet({
    itemList,
    success(res) {
      let action: MapAction = 'view'
      if (loc && res.tapIndex === 1) {
        action = 'navigate'
      }
      openMapUrl(action, loc, keyword, name, address)
    },
  })
}

/** 打开地图 URL */
function openMapUrl(
  action: MapAction,
  loc: { latitude: number; longitude: number } | null,
  keyword: string,
  name: string,
  address: string | null,
): void {
  const viewUrl = buildAmapViewUrl(loc, keyword)
  const webUrl = buildAmapWebUrl(loc, keyword)
  let appUrl = viewUrl

  if (action === 'navigate' && loc) {
    const navUrl = buildAmapNavigationUrl(loc, keyword)
    if (navUrl) appUrl = navUrl
  }

  // 打开中：openExternalUrl 内部有三级降级（URI → Web → 复制）
  openExternalUrl(appUrl, webUrl, `${name} ${address || ''}`.trim())
}

// ========== 生命周期 ==========
onUnload(() => {
  clearResourceCache()
})

onLoad((options: Record<string, string> | undefined) => {
  if (import.meta.env.DEV) {
    console.log('[plan-detail] onLoad fired', { options, timestamp: Date.now() })
  }
  const rawId = options?.id
  const idNum = Number(rawId)
  if (!rawId || !Number.isFinite(idNum) || !Number.isInteger(idNum) || idNum <= 0) {
    if (import.meta.env.DEV) {
      console.warn('[plan-detail] invalid planId', { rawId, idNum })
    }
    loadError.value = 'invalidId'
    isLoading.value = false
    return
  }
  planId.value = idNum
  if (import.meta.env.DEV) {
    console.log('[plan-detail] planId set, calling loadPlan', { planId: idNum })
  }
  void loadPlan()
})

// ========== 数据加载 ==========

async function loadPlan(): Promise<void> {
  const seq = ++_loadSeq
  const t0 = Date.now()

  if (import.meta.env.DEV) {
    console.log(`[plan-detail] loadPlan#${seq} enter`, { _loading, planId: planId.value, t0 })
  }

  if (_loading) {
    if (import.meta.env.DEV) {
      console.warn(`[plan-detail] loadPlan#${seq} blocked by _loading lock`)
    }
    return
  }
  if (planId.value <= 0) {
    loadError.value = 'invalidId'
    isLoading.value = false
    if (import.meta.env.DEV) {
      console.warn(`[plan-detail] loadPlan#${seq} planId <= 0, aborted`)
    }
    return
  }

  _loading = true
  isLoading.value = true
  loadError.value = null
  plan.value = null
  normalizedPlan.value = null
  hasFallbackMarkdown.value = false

  try {
    if (import.meta.env.DEV) {
      console.log(`[plan-detail] loadPlan#${seq} calling getPlanDetail(${planId.value})`)
    }
    const t1 = Date.now()
    plan.value = await getPlanDetail(planId.value)
    if (import.meta.env.DEV) {
      console.log(`[plan-detail] loadPlan#${seq} getPlanDetail resolved`, {
        elapsed: Date.now() - t1,
        hasPlan: plan.value != null,
        hasPlanJson: plan.value?.plan_json != null,
        hasMarkdown: plan.value?.markdown != null,
      })
    }

    // 通过 normalizer 安全获取结构化数据
    if (import.meta.env.DEV) {
      console.log(`[plan-detail] loadPlan#${seq} calling normalizer`)
    }
    const t2 = Date.now()
    const result = normalizeTravelPlanRecord(plan.value)
    normalizedPlan.value = result.data
    if (import.meta.env.DEV) {
      console.log(`[plan-detail] loadPlan#${seq} normalizer done`, {
        elapsed: Date.now() - t2,
        hasData: result.data != null,
        warningCount: result.warnings.length,
      })
    }

    // 开发环境输出 warning
    if (import.meta.env.DEV && result.warnings.length > 0) {
      console.warn('[plan/detail] normalize warnings:', result.warnings)
    }

    // markdown 降级标记
    if (!result.data && plan.value.markdown) {
      hasFallbackMarkdown.value = true
    }
  } catch (err: unknown) {
    if (import.meta.env.DEV) {
      console.error(`[plan-detail] loadPlan#${seq} catch`, {
        elapsed: Date.now() - t0,
        error: err instanceof Error ? err.message : String(err),
      })
    }
    loadError.value = classifyPlanLoadError(err)
  } finally {
    isLoading.value = false
    _loading = false
    if (import.meta.env.DEV) {
      console.log(`[plan-detail] loadPlan#${seq} finally`, {
        totalElapsed: Date.now() - t0,
        isLoading: isLoading.value,
        hasPlan: plan.value != null,
        hasNormalized: normalizedPlan.value != null,
        loadError: loadError.value,
      })
    }
  }
}

function classifyPlanLoadError(err: unknown): PlanLoadError {
  const msg = err instanceof Error ? err.message : String(err ?? '')
  if (msg.includes('不存在') || msg.includes('not found')) return 'notFound'
  if (msg.includes('网络') || msg.includes('network') || msg.includes('超时') || msg.includes('timeout')) return 'network'
  if (msg.includes('fail') || msg.includes('abort')) return 'network'
  return 'unknown'
}

// ========== 删除 ==========

async function handleDelete(): Promise<void> {
  if (isDeleting.value || !plan.value) return

  const modalRes = await uni.showModal({
    title: '删除计划',
    content: `确定删除"${plan.value.title}"吗？删除后无法恢复。`,
    confirmText: '删除',
    confirmColor: '#d93025',
  })
  if (!modalRes.confirm) return

  isDeleting.value = true

  try {
    await deletePlan(plan.value.id)
    uni.showToast({ title: '已删除', icon: 'success' })
    returnToPlanList()
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '删除失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    isDeleting.value = false
  }
}

function returnToPlanList(): void {
  const pages = getCurrentPages()
  if (pages.length > 1) {
    uni.navigateBack()
  } else {
    uni.reLaunch({ url: '/pages/plan/list' })
  }
}

// ========== 重新生成 ==========

function goRegenerate(): void {
  if (!plan.value) return
  const params: string[] = ['from=regenerate']

  params.push(`destination=${encodeURIComponent(plan.value.destination)}`)
  params.push(`days=${plan.value.days}`)

  const b = plan.value.budget
  if (b !== null && b !== undefined && String(b) !== '' && Number.isFinite(Number(b))) {
    params.push(`budget=${encodeURIComponent(String(b))}`)
  }

  const t = normalizedPlan.value?.travelers
  if (t && t > 1) {
    params.push(`travelers=${t}`)
  }

  uni.navigateTo({ url: `/pages/plan/generate?${params.join('&')}` })
}

// ========== 分享 ==========

/** 分享管理弹窗可见性 */
const showShareManager = ref(false)
/** 创建分享弹窗可见性 */
const showShareCreate = ref(false)
/** 分享列表数据 */
const shareList = ref<ShareInfo[]>([])
/** 分享列表加载中 */
const shareListLoading = ref(false)
/** 创建分享进行中 */
const shareCreating = ref(false)
/** 撤销中的 share_id 集合 */
const shareRevokingIds = ref<Set<number>>(new Set())
/** 创建分享 — 有效期（小时） */
const createShareExpires = ref(72)
/** 创建分享 — 是否公开预算 */
const createShareIncludeBudget = ref(false)
/** 创建分享结果（成功后显示） */
const createdShareResult = ref<ShareCreated | null>(null)
/**
 * 页面内存中的 Token 映射：share_id → share_token
 *
 * 后端列表接口 share_url 中的 token 是哈希值，不可用于公开访问。
 * 只有创建时返回的原始 share_token 才是有效凭证。
 * 此映射仅在页面生命周期内有效，不持久化。
 */
const createdShareTokens = new Map<number, string>()

/** 分享完整计划 — 弹出选项菜单 */
function handleShareFullPlan(): void {
  if (!plan.value || !normalizedPlan.value) return

  uni.showActionSheet({
    itemList: ['复制计划文本', '创建公开分享', '管理分享记录'],
    success(res) {
      if (res.tapIndex === 0) {
        // 复制计划文本 → 现有流程
        showTextShareOptions()
      } else if (res.tapIndex === 1) {
        // 创建公开分享
        openShareCreate()
      } else if (res.tapIndex === 2) {
        // 管理分享记录
        openShareManager()
      }
    },
  })
}

/** 复制计划文本（保留原逻辑） */
function showTextShareOptions(): void {
  if (!plan.value || !normalizedPlan.value) return

  uni.showActionSheet({
    itemList: ['系统分享', '复制行程文本'],
    success(res) {
      const text = buildFullPlanShareText(plan.value!, normalizedPlan.value!)
      const title = normalizedPlan.value?.title || plan.value?.title || '旅行计划'
      if (res.tapIndex === 0) {
        void shareText(title, text)
      } else {
        void copyShareText(text)
      }
    },
  })
}

/** 分享单日行程（保留原逻辑不变） */
function handleShareDay(dayIndex: number): void {
  if (!normalizedPlan.value) return
  const day = normalizedPlan.value.itinerary[dayIndex]
  if (!day) return

  const destName = normalizedPlan.value.destination.name || plan.value?.destination || ''

  uni.showActionSheet({
    itemList: ['系统分享', '复制行程文本'],
    success(res) {
      const text = buildDayShareText(day, destName)
      const title = `${destName}第 ${day.day} 天行程`
      if (res.tapIndex === 0) {
        void shareText(title, text)
      } else {
        void copyShareText(text)
      }
    },
  })
}

// ========== 分享管理 ==========

/** 打开分享管理弹窗并加载列表 */
async function openShareManager(): Promise<void> {
  if (!plan.value) return
  showShareManager.value = true
  await loadShareList()
}

/** 关闭分享管理弹窗 */
function closeShareManager(): void {
  showShareManager.value = false
}

/** 加载分享列表 */
async function loadShareList(): Promise<void> {
  if (!plan.value) return
  shareListLoading.value = true

  const result = await listPlanShares(plan.value.id)
  shareList.value = result.data ?? []
  shareListLoading.value = false
}

/** 撤销分享（二次确认后） */
async function handleRevokeShare(share: ShareInfo): Promise<void> {
  if (!plan.value || shareRevokingIds.value.has(share.share_id)) return

  const modalRes = await uni.showModal({
    title: '撤销分享',
    content: '撤销后，已分享的链接将立即失效。确定撤销？',
    confirmText: '撤销',
    confirmColor: '#d93025',
  })
  if (!modalRes.confirm) return

  // 标记撤销中
  const newSet = new Set(shareRevokingIds.value)
  newSet.add(share.share_id)
  shareRevokingIds.value = newSet

  try {
    await revokePlanShare(plan.value.id, share.share_id)
    uni.showToast({ title: '已撤销', icon: 'success' })
    // 刷新列表
    await loadShareList()
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '撤销失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    const newSet2 = new Set(shareRevokingIds.value)
    newSet2.delete(share.share_id)
    shareRevokingIds.value = newSet2
  }
}

// ========== 创建分享 ==========

/** 打开创建分享弹窗 */
function openShareCreate(): void {
  createdShareResult.value = null
  createShareExpires.value = 72
  createShareIncludeBudget.value = false
  showShareCreate.value = true
}

/** 关闭创建分享弹窗 */
function closeShareCreate(): void {
  showShareCreate.value = false
  createdShareResult.value = null
}

/** 执行创建分享 */
async function handleCreateShare(): Promise<void> {
  if (!plan.value || shareCreating.value) return

  shareCreating.value = true
  createdShareResult.value = null

  const result = await createPlanShare(plan.value.id, {
    expiresInHours: createShareExpires.value,
    includeBudget: createShareIncludeBudget.value,
  })

  shareCreating.value = false

  if (result.data) {
    createdShareResult.value = result.data
    // 保存到页面内存映射，供管理列表使用
    createdShareTokens.set(result.data.share_id, result.data.share_token)
  } else {
    uni.showToast({ title: result.error || '创建失败', icon: 'none' })
  }
}

/** 复制 share_token（创建成功后） */
function copyShareToken(): void {
  if (!createdShareResult.value) return
  uni.setClipboardData({
    data: createdShareResult.value.share_token,
    success: () => {
      uni.showToast({ title: '分享令牌已复制', icon: 'success' })
    },
  })
}

/** 预览分享页面（本地导航） */
function previewSharePage(token: string): void {
  const encoded = encodeURIComponent(token)
  uni.navigateTo({
    url: `/pages/plan/share?token=${encoded}`,
  })
}

/** 获取指定 share 的有效 Token（仅在页面内存映射中查找） */
function getAccessibleToken(shareId: number): string | null {
  return createdShareTokens.get(shareId) ?? null
}

/** 从管理列表查看分享 — 仅当有有效 Token */
function viewShareFromList(shareId: number): void {
  const accessibleToken = getAccessibleToken(shareId)
  if (!accessibleToken) {
    uni.showToast({ title: '当前设备没有该分享的访问凭证', icon: 'none', duration: 2500 })
    return
  }
  previewSharePage(accessibleToken)
}

/** 从管理列表复制 Token — 仅当有有效 Token */
function copyShareTokenFromList(shareId: number): void {
  const accessibleToken = getAccessibleToken(shareId)
  if (!accessibleToken) {
    uni.showToast({ title: '当前设备没有该分享的访问凭证', icon: 'none', duration: 2500 })
    return
  }
  uni.setClipboardData({
    data: accessibleToken,
    success: () => {
      uni.showToast({ title: '分享 Token 已复制', icon: 'success' })
    },
  })
}

/** 复制公开 H5 页面链接 */
function copySharePageUrl(token: string): void {
  const url = getPublicSharePageUrl(token)
  if (!url) {
    uni.showToast({ title: '公开网页地址尚未配置', icon: 'none', duration: 2500 })
    return
  }
  uni.setClipboardData({
    data: url,
    success: () => {
      uni.showToast({ title: '分享链接已复制', icon: 'success' })
    },
  })
}

/** 获取公开 H5 页面 URL */
function getPublicSharePageUrl(token: string): string | null {
  const publicBase = import.meta.env.VITE_PUBLIC_H5_BASE_URL
  if (!publicBase) return null
  const base = String(publicBase).trim().replace(/\/+$/, '')
  const encoded = encodeURIComponent(token)
  return `${base}/#/pages/plan/share?token=${encoded}`
}

/** 是否可复制公开链接 */
const hasPublicBaseUrl = computed(() => {
  return !!(import.meta.env.VITE_PUBLIC_H5_BASE_URL as string | undefined)
})

// ========== 格式化辅助 ==========

/** 格式化日期时间为可读字符串 */
function fmtDateTime(dateStr: string): string {
  if (!dateStr) return '--'
  // 截取到分钟：2026-07-29T07:35:13 → 2026-07-29 07:35
  return dateStr.slice(0, 16).replace('T', ' ')
}

/** 分享状态标签 */
function shareStatusLabel(status: string): string {
  return status === 'active' ? '有效' : '已撤销'
}

/** 计算剩余有效时间 */
function shareRemaining(expiresAt: string): string {
  if (!expiresAt) return '--'
  const now = Date.now()
  const exp = Date.parse(expiresAt)
  if (isNaN(exp)) return '--'
  const remaining = exp - now
  if (remaining <= 0) return '已过期'
  const hours = Math.floor(remaining / 3600000)
  const minutes = Math.floor((remaining % 3600000) / 60000)
  if (hours >= 24) {
    const days = Math.floor(hours / 24)
    return `剩余 ${days} 天 ${hours % 24} 小时`
  }
  if (hours > 0) return `剩余 ${hours} 小时 ${minutes} 分钟`
  return `剩余 ${minutes} 分钟`
}

// ========== 展示常量 ==========
const PERIOD_LABELS: Record<string, string> = {
  morning: '上午',
  noon: '中午',
  afternoon: '下午',
  evening: '傍晚',
  night: '晚上',
}

// ========== 格式化函数 ==========
function fmtCost(cost: number | null | undefined): string {
  if (cost === undefined || cost === null) return '--'
  if (cost === 0) return '免费'
  return `¥${cost}`
}

function fmtNum(n: number | null | undefined): string {
  if (n === undefined || n === null) return '--'
  return String(n)
}

// ========== 资源导航 ==========

function canOpenResource(type: string, id: number | null): boolean {
  return getResourceDetailUrl(type as TravelResourceType | 'unknown', id) !== null
}

function handleResourceTap(type: string, id: number | null): void {
  openResourceDetail(type as TravelResourceType | 'unknown', id)
}

// ========== 实时路线 ==========

interface PlanTransitSegment {
  originType: TransitEndpointType
  originId: number
  originName: string
  destinationType: TransitEndpointType
  destinationId: number
  destinationName: string
}

function getTransitSegment(
  items: PlanTimelineItem[],
  index: number,
): PlanTransitSegment | null {
  const current = items[index]
  const next = items[index + 1]
  if (!current || !next) return null

  const ct = current.resource_type as string
  const nt = next.resource_type as string
  if (!isNavigableResourceType(ct) || !isNavigableResourceType(nt)) return null
  if (!isValidResourceId(current.resource_id) || !isValidResourceId(next.resource_id)) return null
  if (ct === nt && current.resource_id === next.resource_id) return null

  return {
    originType: ct,
    originId: current.resource_id,
    originName: current.name,
    destinationType: nt,
    destinationId: next.resource_id,
    destinationName: next.name,
  }
}

function transitCity(): string {
  if (normalizedPlan.value?.destination?.name) return normalizedPlan.value.destination.name
  return plan.value?.destination ?? ''
}

// ========== 展示常量 ==========

function resourceLabel(item: PlanTimelineItem | PlanMeal | PlanHotel): string {
  return getResourceTypeLabel(item.resource_type, item.raw_resource_type)
}

/** 判断预算明细是否有至少一个非 null 值 */
function hasAnyBreakdown(b: { tickets: number | null; food: number | null; lodging: number | null; transport: number | null; other: number | null }): boolean {
  return b.tickets !== null || b.food !== null || b.lodging !== null || b.transport !== null || b.other !== null
}
</script>

<template>
  <view class="detail-page">
    <NavBar title="计划详情" :show-back="true" />

    <!-- 加载中 -->
    <view v-if="isLoading" class="detail-loading">
      <text>加载中...</text>
    </view>

    <!-- 非法 ID -->
    <view v-else-if="loadError === 'invalidId'" class="detail-empty">
      <text class="detail-error-title">计划参数无效</text>
      <view class="detail-action-btn" @tap="returnToPlanList">
        <text>返回列表</text>
      </view>
    </view>

    <!-- 不存在 -->
    <view v-else-if="loadError === 'notFound'" class="detail-empty">
      <text class="detail-error-title">计划不存在或已被删除</text>
      <view class="detail-action-btn" @tap="returnToPlanList">
        <text>返回列表</text>
      </view>
    </view>

    <!-- 网络/未知错误 -->
    <view v-else-if="loadError === 'network' || loadError === 'unknown'" class="detail-empty">
      <text class="detail-error-title">{{ loadError === 'network' ? '网络请求失败，请检查网络后重试' : '计划加载失败' }}</text>
      <view class="detail-action-row">
        <view class="detail-action-btn" @tap="loadPlan()">
          <text>重新加载</text>
        </view>
        <view class="detail-action-btn secondary" @tap="returnToPlanList">
          <text>返回列表</text>
        </view>
      </view>
    </view>

    <scroll-view v-else-if="plan && normalizedPlan" class="detail-scroll" scroll-y>
      <!-- 标题和基本信息 -->
      <view class="info-card">
        <text class="info-title">{{ normalizedPlan.title || plan.title }}</text>
        <text class="info-summary" v-if="normalizedPlan.summary">{{ normalizedPlan.summary }}</text>

        <view class="info-grid">
          <view class="info-item">
            <text class="info-label">目的地</text>
            <text class="info-value">{{ plan.destination }}</text>
          </view>
          <view class="info-item">
            <text class="info-label">天数</text>
            <text class="info-value">{{ plan.days }} 天</text>
          </view>
          <view class="info-item" v-if="normalizedPlan.travelers > 1">
            <text class="info-label">人数</text>
            <text class="info-value">{{ normalizedPlan.travelers }} 人</text>
          </view>
          <view class="info-item" v-if="plan.budget">
            <text class="info-label">预算</text>
            <text class="info-value">¥{{ plan.budget }}</text>
          </view>
          <view class="info-item" v-if="normalizedPlan.budget.estimated_total !== null">
            <text class="info-label">预估费用</text>
            <text class="info-value highlight">¥{{ normalizedPlan.budget.estimated_total }}</text>
          </view>
        </view>
      </view>

      <!-- 每日行程 -->
      <view class="itinerary-section" v-if="normalizedPlan.itinerary.length > 0">
        <text class="section-title">行程安排</text>

        <view v-for="(day, di) in normalizedPlan.itinerary" :key="di" class="day-card">
          <view class="day-header">
            <view class="day-header-left">
              <text class="day-num">第 {{ day.day }} 天</text>
              <text class="day-theme" v-if="day.theme">{{ day.theme }}</text>
            </view>
            <text class="day-share-btn" @tap.stop="handleShareDay(di)">分享当天</text>
          </view>

          <text class="day-summary" v-if="day.summary">{{ day.summary }}</text>
          <text class="day-weather" v-if="day.weather_note">🌤️ {{ day.weather_note }}</text>

          <!-- 行程项目 -->
          <view class="timeline" v-if="day.items.length > 0">
            <view v-for="(item, ii) in day.items" :key="ii" class="timeline-item">
              <view class="timeline-dot" :class="item.resource_type === 'unknown' ? '' : item.resource_type" />
              <view class="timeline-content">
                <view class="tl-header">
                  <text
                    class="tl-name"
                    :class="{ 'tl-name-link': canOpenResource(item.resource_type, item.resource_id) }"
                    @tap="canOpenResource(item.resource_type, item.resource_id) && handleResourceTap(item.resource_type, item.resource_id)"
                  >{{ item.name }}</text>
                  <text class="tl-type">{{ resourceLabel(item) }}</text>
                </view>
                <text class="tl-meta" v-if="item.start_time || item.end_time">
                  ⏰ {{ item.start_time || '?' }} - {{ item.end_time || '?' }}
                </text>
                <text class="tl-meta" v-if="item.address">📍 {{ item.address }}</text>
                <text class="tl-meta" v-if="item.duration_minutes !== null">
                  ⏱️ {{ item.duration_minutes }} 分钟
                </text>
                <text class="tl-cost" v-if="item.estimated_cost !== null">
                  💰 {{ fmtCost(item.estimated_cost) }}
                </text>
                <text class="tl-reason" v-if="item.reason">💡 {{ item.reason }}</text>
                <text class="tl-transport" v-if="item.transport_to_next">
                  🚗 {{ item.transport_to_next }}
                </text>

                <!-- 实时路线 + 高德两点路线 -->
                <TransitRoutePanel
                  v-if="getTransitSegment(day.items, ii)"
                  :origin-type="getTransitSegment(day.items, ii)!.originType"
                  :origin-id="getTransitSegment(day.items, ii)!.originId"
                  :origin-name="getTransitSegment(day.items, ii)!.originName"
                  :destination-type="getTransitSegment(day.items, ii)!.destinationType"
                  :destination-id="getTransitSegment(day.items, ii)!.destinationId"
                  :destination-name="getTransitSegment(day.items, ii)!.destinationName"
                  :city="transitCity()"
                  :amap-loading="routeLoadingKeys.has(routeKey(di, ii))"
                  @open-amap-route="handleOpenAmapRoute(
                    day.items[ii],
                    day.items[ii + 1],
                    di,
                    ii,
                    $event
                  )"
                />
              </view>
            </view>
          </view>

          <!-- 用餐 -->
          <view class="meals-section" v-if="day.meals.length > 0">
            <text class="meals-title">🍜 用餐</text>
            <view v-for="(meal, mi) in day.meals" :key="mi" class="meal-item">
              <text>{{ PERIOD_LABELS[meal.period] || meal.period }}：</text>
              <text
                :class="{ 'tl-name-link': canOpenResource(meal.resource_type, meal.resource_id) }"
                @tap="canOpenResource(meal.resource_type, meal.resource_id) && handleResourceTap(meal.resource_type, meal.resource_id)"
              >{{ meal.name }}</text>
              <text v-if="meal.estimated_cost !== null"> {{ fmtCost(meal.estimated_cost) }}</text>
            </view>
          </view>

          <!-- 住宿 -->
          <view class="hotel-section" v-if="day.hotel">
            <text class="meals-title">🏨 住宿</text>
            <text
              class="hotel-name"
              :class="{ 'tl-name-link': canOpenResource(day.hotel.resource_type, day.hotel.resource_id) }"
              @tap="canOpenResource(day.hotel.resource_type, day.hotel.resource_id) && handleResourceTap(day.hotel.resource_type, day.hotel.resource_id)"
            >{{ day.hotel.name }}</text>
            <view class="tl-address-row" v-if="day.hotel.address || day.hotel.name">
              <text class="tl-meta" v-if="day.hotel.address">📍 {{ day.hotel.address }}</text>
              <text
                class="tl-map-btn"
                :class="{ loading: mapLoadingKeys.has(nodeKey('hotel', di, 0)) }"
                @tap.stop="handleOpenMap(day.hotel, di, 0)"
              >{{ mapLoadingKeys.has(nodeKey('hotel', di, 0)) ? '查询中...' : '🗺️ 地图' }}</text>
            </view>
            <text class="tl-cost" v-if="day.hotel.estimated_cost !== null">💰 {{ fmtCost(day.hotel.estimated_cost) }}</text>
          </view>

          <!-- 当日费用 -->
          <view class="day-cost" v-if="day.daily_estimated_cost !== null">
            <text>本日预估：{{ fmtCost(day.daily_estimated_cost) }}</text>
          </view>
        </view>
      </view>

      <!-- 预算明细 -->
      <view class="budget-card" v-if="hasAnyBreakdown(normalizedPlan.budget.breakdown)">
        <text class="section-title">预算明细</text>
        <view class="budget-row">
          <text>门票</text><text>{{ fmtCost(normalizedPlan.budget.breakdown.tickets) }}</text>
        </view>
        <view class="budget-row">
          <text>餐饮</text><text>{{ fmtCost(normalizedPlan.budget.breakdown.food) }}</text>
        </view>
        <view class="budget-row">
          <text>住宿</text><text>{{ fmtCost(normalizedPlan.budget.breakdown.lodging) }}</text>
        </view>
        <view class="budget-row">
          <text>交通</text><text>{{ fmtCost(normalizedPlan.budget.breakdown.transport) }}</text>
        </view>
        <view class="budget-row">
          <text>其他</text><text>{{ fmtCost(normalizedPlan.budget.breakdown.other) }}</text>
        </view>
        <view class="budget-row total" v-if="normalizedPlan.budget.estimated_total !== null">
          <text>合计</text><text>{{ fmtCost(normalizedPlan.budget.estimated_total) }}</text>
        </view>
      </view>

      <!-- 旅行贴士 -->
      <view class="tips-card" v-if="normalizedPlan.tips.length > 0">
        <text class="section-title">旅行贴士</text>
        <text v-for="(tip, ti) in normalizedPlan.tips" :key="ti" class="tip-item">• {{ tip }}</text>
      </view>

      <!-- 假设与说明 -->
      <view class="assumptions-card" v-if="normalizedPlan.assumptions.length > 0">
        <text class="section-title">假设与数据说明</text>
        <text v-for="(a, ai) in normalizedPlan.assumptions" :key="ai" class="tip-item">• {{ a }}</text>
      </view>

      <!-- 页脚 -->
      <view class="detail-footer">
        <text>本计划由行知 AI 助手生成</text>
        <text>实际价格、开放时间和天气可能变化，出行前请再次确认</text>
      </view>

      <!-- 操作区 -->
      <view class="detail-actions">
        <view class="detail-action-btn" @tap="handleShareFullPlan">
          <text>分享计划</text>
        </view>
        <view class="detail-action-btn" @tap="goRegenerate">
          <text>重新生成</text>
        </view>
        <view
          class="detail-action-btn danger"
          :class="{ disabled: isDeleting }"
          @tap="handleDelete"
        >
          <text>{{ isDeleting ? '删除中...' : '删除计划' }}</text>
        </view>
      </view>
    </scroll-view>

    <!-- markdown 降级 -->
    <scroll-view v-else-if="plan && hasFallbackMarkdown && plan.markdown" class="detail-scroll" scroll-y>
      <view class="info-card">
        <text class="info-title">{{ plan.title }}</text>
        <text class="info-summary">计划内容暂不支持结构化展示，以下为原始内容：</text>
      </view>
      <view class="tips-card">
        <text class="tip-item" selectable>{{ plan.markdown }}</text>
      </view>
    </scroll-view>

    <!-- 内容不可用（无 error 但无 normalizedPlan 也无 markdown） -->
    <view v-else-if="!isLoading && !loadError" class="detail-empty">
      <text>计划内容暂不可用</text>
    </view>

    <!-- ========== 创建分享弹窗 ========== -->
    <view class="share-modal-mask" v-if="showShareCreate" @tap="closeShareCreate">
      <view class="share-modal" @tap.stop>
        <view class="share-modal-header">
          <text class="share-modal-title">创建公开分享</text>
          <text class="share-modal-close" @tap="closeShareCreate">✕</text>
        </view>

        <!-- 创建表单（未完成前） -->
        <view v-if="!createdShareResult" class="share-modal-body">
          <view class="share-form-group">
            <text class="share-form-label">有效期</text>
            <view class="share-stepper-row">
              <button class="share-stepper-btn" :disabled="createShareExpires <= 1" @tap="createShareExpires = Math.max(1, createShareExpires - 24)">-24h</button>
              <text class="share-stepper-value">{{ createShareExpires }} 小时</text>
              <button class="share-stepper-btn" :disabled="createShareExpires >= 720" @tap="createShareExpires = Math.min(720, createShareExpires + 24)">+24h</button>
            </view>
            <text class="share-form-hint">{{ createShareExpires >= 24 ? (Math.floor(createShareExpires / 24) + ' 天 ' + (createShareExpires % 24 > 0 ? createShareExpires % 24 + ' 小时' : '')) : createShareExpires + ' 小时' }}</text>
          </view>

          <view class="share-form-group">
            <text class="share-form-label">公开预算</text>
            <switch :checked="createShareIncludeBudget" @change="(e: any) => createShareIncludeBudget = e.detail.value" color="#4A90D9" />
          </view>

          <view class="share-form-notice">
            <text>注意：当前"公开预算"功能暂不可用（后端已知问题），公开分享默认不包含预算信息。</text>
          </view>

          <button
            class="share-create-btn"
            :disabled="shareCreating || createShareIncludeBudget"
            @tap="handleCreateShare"
          >
            <text>{{ shareCreating ? '创建中...' : (createShareIncludeBudget ? '预算公开暂不可用' : '创建分享链接') }}</text>
          </button>
        </view>

        <!-- 创建成功结果 -->
        <view v-else class="share-modal-body">
          <view class="share-result-icon">✓</view>
          <text class="share-result-title">分享已创建</text>

          <view class="share-result-info">
            <text class="share-result-label">分享令牌</text>
            <text class="share-result-value token">{{ createdShareResult.share_token }}</text>
          </view>

          <view class="share-result-info">
            <text class="share-result-label">有效期至</text>
            <text class="share-result-value">{{ fmtDateTime(createdShareResult.expires_at) }}</text>
          </view>

          <view class="share-result-notice">
            <text>公开页面 URL 将在配置 H5 域名后可用。</text>
          </view>

          <view class="share-result-actions">
            <view class="detail-action-btn" @tap="previewSharePage(createdShareResult.share_token)">
              <text>预览分享页面</text>
            </view>
            <view class="detail-action-btn" v-if="hasPublicBaseUrl" @tap="copySharePageUrl(createdShareResult.share_token)">
              <text>复制链接</text>
            </view>
            <view class="detail-action-btn secondary" @tap="closeShareCreate">
              <text>关闭</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- ========== 分享管理弹窗 ========== -->
    <view class="share-modal-mask" v-if="showShareManager" @tap="closeShareManager">
      <view class="share-modal share-manager-modal" @tap.stop>
        <view class="share-modal-header">
          <text class="share-modal-title">分享管理</text>
          <text class="share-modal-close" @tap="closeShareManager">✕</text>
        </view>

        <view class="share-modal-body">
          <!-- 加载中 -->
          <view v-if="shareListLoading" class="share-list-status">
            <text>加载中...</text>
          </view>

          <!-- 空列表 -->
          <view v-else-if="shareList.length === 0" class="share-list-status">
            <text class="share-empty-icon">🔗</text>
            <text>暂无分享记录</text>
          </view>

          <!-- 分享列表 -->
          <view v-else class="share-list">
            <view
              v-for="share in shareList"
              :key="share.share_id"
              class="share-list-item"
              :class="{ revoked: share.status === 'revoked' }"
            >
              <view class="share-item-header">
                <text class="share-item-status" :class="share.status">
                  {{ shareStatusLabel(share.status) }}
                </text>
                <text class="share-item-time">{{ shareRemaining(share.expires_at) }}</text>
              </view>

              <view class="share-item-meta">
                <text class="share-item-label">创建时间</text>
                <text class="share-item-value">{{ fmtDateTime(share.created_at) }}</text>
              </view>

              <view class="share-item-meta">
                <text class="share-item-label">过期时间</text>
                <text class="share-item-value">{{ fmtDateTime(share.expires_at) }}</text>
              </view>

              <view class="share-item-meta" v-if="share.include_budget">
                <text class="share-item-label">预算</text>
                <text class="share-item-value">已公开</text>
              </view>

              <!-- 是否有有效访问凭证 -->
              <view
                v-if="share.status === 'active' && !getAccessibleToken(share.share_id)"
                class="share-no-token-hint"
              >
                <text>当前设备没有该分享的访问凭证，请重新创建分享。</text>
              </view>

              <!-- 操作区 -->
              <view class="share-item-actions">
                <template v-if="getAccessibleToken(share.share_id)">
                  <view
                    class="share-action-btn"
                    @tap="viewShareFromList(share.share_id)"
                  >
                    <text>查看</text>
                  </view>
                  <view
                    class="share-action-btn"
                    @tap="copyShareTokenFromList(share.share_id)"
                  >
                    <text>复制 Token</text>
                  </view>
                  <view
                    v-if="share.status === 'active' && hasPublicBaseUrl"
                    class="share-action-btn"
                    @tap="copySharePageUrl(getAccessibleToken(share.share_id)!)"
                  >
                    <text>复制链接</text>
                  </view>
                </template>
                <view
                  v-if="share.status === 'active'"
                  class="share-action-btn danger"
                  :class="{ revoking: shareRevokingIds.has(share.share_id) }"
                  @tap="handleRevokeShare(share)"
                >
                  <text>{{ shareRevokingIds.has(share.share_id) ? '撤销中...' : '撤销' }}</text>
                </view>
              </view>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.detail-page {
  min-height: 100vh;
  background: #f5f5f5;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.detail-loading, .detail-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 200rpx 48rpx 0;
  font-size: 28rpx;
  color: #999;
  box-sizing: border-box;
  width: 100%;
}

.detail-scroll {
  padding: 24rpx 32rpx;
  padding-bottom: 60rpx;
  width: 100%;
  box-sizing: border-box;
}

// Info card
.info-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.info-title {
  font-size: 36rpx;
  font-weight: 700;
  color: #333;
  display: block;
  margin-bottom: 12rpx;
}

.info-summary {
  font-size: 26rpx;
  color: #666;
  display: block;
  margin-bottom: 16rpx;
  line-height: 1.5;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.info-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
  min-width: 0;
}

.info-item {
  flex: 1;
  min-width: 40%;
}

.info-label {
  font-size: 24rpx;
  color: #999;
  display: block;
}

.info-value {
  font-size: 28rpx;
  color: #333;
  font-weight: 600;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.info-value.highlight {
  color: #FF6B35;
}

// Section title
.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #333;
  display: block;
  margin-bottom: 16rpx;
}

// Day card
.day-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.day-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 12rpx;
  min-width: 0;
  width: 100%;
}

.day-header-left {
  display: flex;
  align-items: center;
  gap: 16rpx;
  min-width: 0;
  flex: 1;
}

.day-num {
  background: #4A90D9;
  color: #fff;
  font-size: 24rpx;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  flex-shrink: 0;
}

.day-theme {
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

// Day share button
.day-share-btn {
  font-size: 24rpx;
  color: #4A90D9;
  padding: 6rpx 16rpx;
  border: 1rpx solid #4A90D9;
  border-radius: 8rpx;
  flex-shrink: 0;
  white-space: nowrap;
}

.day-summary {
  font-size: 26rpx;
  color: #666;
  display: block;
  margin-bottom: 12rpx;
}

.day-weather {
  font-size: 24rpx;
  color: #999;
  display: block;
  margin-bottom: 12rpx;
}

// Timeline
.timeline {
  padding-left: 12rpx;
}

.timeline-item {
  display: flex;
  gap: 16rpx;
  margin-bottom: 20rpx;
}

.timeline-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 8rpx;
  margin-top: 8rpx;
  flex-shrink: 0;
}

.timeline-dot.scenic_spot { background: #4A90D9; }
.timeline-dot.restaurant { background: #FF6B35; }
.timeline-dot.hotel { background: #7B68EE; }
.timeline-dot.general_activity { background: #ccc; }

.timeline-content {
  flex: 1;
  min-width: 0;
  box-sizing: border-box;
}

.tl-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  min-width: 0;
}

.tl-name {
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.tl-name-link {
  color: #4A90D9;
  text-decoration: underline;
}

.tl-type {
  font-size: 22rpx;
  color: #999;
  background: #f0f0f0;
  padding: 2rpx 12rpx;
  border-radius: 8rpx;
  flex-shrink: 0;
  white-space: nowrap;
}

.tl-meta {
  font-size: 24rpx;
  color: #999;
  display: block;
  margin-top: 4rpx;
}

// Map button
.tl-address-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-top: 4rpx;
  min-width: 0;

  .tl-meta {
    margin-top: 0;
    flex: 1;
    min-width: 0;
    overflow-wrap: anywhere;
    word-break: break-word;
  }
}

.tl-map-btn {
  font-size: 22rpx;
  color: #4A90D9;
  padding: 4rpx 12rpx;
  border: 1rpx solid #4A90D9;
  border-radius: 8rpx;
  white-space: nowrap;
  flex-shrink: 0;
}

.tl-map-btn.loading {
  color: #999;
  border-color: #ccc;
}

.tl-cost {
  font-size: 24rpx;
  color: #FF6B35;
  margin-top: 4rpx;
}

.tl-reason {
  font-size: 24rpx;
  color: #666;
  margin-top: 4rpx;
  font-style: italic;
}

.tl-transport {
  font-size: 24rpx;
  color: #999;
  margin-top: 4rpx;
}

// Meals & Hotel
.meals-section, .hotel-section {
  margin-top: 16rpx;
  padding-top: 16rpx;
  border-top: 1rpx solid #f0f0f0;
}

.meals-title {
  font-size: 26rpx;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 8rpx;
}

.meal-item {
  font-size: 26rpx;
  color: #666;
  margin-bottom: 4rpx;
}

.hotel-name {
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
  display: block;
}

// Day cost
.day-cost {
  margin-top: 16rpx;
  padding-top: 12rpx;
  border-top: 1rpx solid #f0f0f0;
  text-align: right;
  font-size: 26rpx;
  color: #FF6B35;
  font-weight: 600;
}

// Budget card
.budget-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.budget-row {
  display: flex;
  justify-content: space-between;
  font-size: 28rpx;
  color: #333;
  padding: 8rpx 0;
  min-width: 0;
}

.budget-row.total {
  border-top: 1rpx solid #eee;
  margin-top: 8rpx;
  padding-top: 12rpx;
  font-weight: 700;
}

// Tips & Assumptions
.tips-card, .assumptions-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.tip-item {
  font-size: 26rpx;
  color: #666;
  display: block;
  padding: 6rpx 0;
  line-height: 1.5;
  overflow-wrap: anywhere;
  word-break: break-word;
}

// Footer
.detail-footer {
  text-align: center;
  padding: 32rpx 0;
  font-size: 24rpx;
  color: #bbb;
  width: 100%;
  box-sizing: border-box;

  text {
    display: block;
    margin-bottom: 8rpx;
    overflow-wrap: anywhere;
  }
}

// Error state
.detail-error-title {
  font-size: 30rpx;
  color: #666;
  margin-bottom: 32rpx;
  display: block;
}

.detail-action-row {
  display: flex;
  gap: 24rpx;
}

.detail-action-btn {
  padding: 14rpx 40rpx;
  border: 1px solid #4A90D9;
  border-radius: 32rpx;
  font-size: 28rpx;
  color: #4A90D9;
  text-align: center;
}

.detail-action-btn.secondary {
  border-color: #ccc;
  color: #999;
}

.detail-action-btn.danger {
  border-color: #d93025;
  color: #d93025;
}

.detail-action-btn.disabled {
  opacity: 0.5;
}

// Action bar
.detail-actions {
  display: flex;
  gap: 24rpx;
  padding: 24rpx 0 40rpx;
  min-width: 0;
  width: 100%;
  box-sizing: border-box;

  .detail-action-btn {
    flex: 1;
    min-width: 0;
    box-sizing: border-box;
  }
}

// ==================== 分享弹窗 ====================

.share-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.share-modal {
  background: #fff;
  border-radius: 24rpx 24rpx 0 0;
  width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.share-manager-modal {
  max-height: 70vh;
}

.share-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32rpx 32rpx 20rpx;
  border-bottom: 1rpx solid #f0f0f0;
  flex-shrink: 0;
}

.share-modal-title {
  font-size: 32rpx;
  font-weight: 700;
  color: #333;
}

.share-modal-close {
  font-size: 36rpx;
  color: #999;
  padding: 8rpx;
}

.share-modal-body {
  padding: 24rpx 32rpx 32rpx;
  overflow-y: auto;
  flex: 1;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
}

// Form
.share-form-group {
  margin-bottom: 24rpx;
}

.share-form-label {
  font-size: 28rpx;
  color: #333;
  font-weight: 600;
  display: block;
  margin-bottom: 12rpx;
}

.share-form-hint {
  font-size: 24rpx;
  color: #999;
  margin-top: 8rpx;
  display: block;
}

.share-form-notice {
  background: #fff8e1;
  border-radius: 12rpx;
  padding: 16rpx;
  margin-bottom: 24rpx;

  text {
    font-size: 24rpx;
    color: #e6a23c;
    line-height: 1.5;
  }
}

.share-stepper-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.share-stepper-btn {
  padding: 10rpx 24rpx;
  border-radius: 12rpx;
  background: #f0f0f0;
  font-size: 26rpx;
  color: #333;
  border: none;
  line-height: 1.4;
}

.share-stepper-btn[disabled] {
  opacity: 0.4;
}

.share-stepper-value {
  font-size: 28rpx;
  font-weight: 600;
  min-width: 120rpx;
  text-align: center;
}

.share-create-btn {
  width: 100%;
  height: 80rpx;
  background: #4A90D9;
  color: #fff;
  font-size: 30rpx;
  border-radius: 40rpx;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

.share-create-btn[disabled] {
  background: #ccc;
}

// Result
.share-result-icon {
  width: 80rpx;
  height: 80rpx;
  border-radius: 40rpx;
  background: #4A90D9;
  color: #fff;
  font-size: 40rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16rpx;
}

.share-result-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #333;
  text-align: center;
  display: block;
  margin-bottom: 24rpx;
}

.share-result-info {
  margin-bottom: 16rpx;
}

.share-result-label {
  font-size: 24rpx;
  color: #999;
  display: block;
  margin-bottom: 4rpx;
}

.share-result-value {
  font-size: 26rpx;
  color: #333;
  word-break: break-all;
}

.share-result-value.token {
  font-family: monospace;
  background: #f5f5f5;
  padding: 8rpx 12rpx;
  border-radius: 8rpx;
  display: block;
}

.share-result-notice {
  background: #e8f0fe;
  border-radius: 12rpx;
  padding: 16rpx;
  margin: 16rpx 0;

  text {
    font-size: 24rpx;
    color: #4A90D9;
    line-height: 1.5;
  }
}

.share-result-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 24rpx;

  .detail-action-btn {
    flex: 1;
  }
}

// List
.share-list-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60rpx 0;
  font-size: 28rpx;
  color: #999;
}

.share-empty-icon {
  font-size: 64rpx;
  margin-bottom: 16rpx;
}

.share-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.share-list-item {
  background: #f8f8f8;
  border-radius: 16rpx;
  padding: 20rpx;
}

.share-list-item.revoked {
  opacity: 0.6;
}

.share-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12rpx;
}

.share-item-status {
  font-size: 24rpx;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
}

.share-item-status.active {
  background: #e8f5e9;
  color: #2e7d32;
}

.share-item-status.revoked {
  background: #f5f5f5;
  color: #999;
}

.share-item-time {
  font-size: 24rpx;
  color: #999;
}

.share-item-meta {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8rpx;
}

.share-item-label {
  font-size: 24rpx;
  color: #999;
}

.share-item-value {
  font-size: 24rpx;
  color: #333;
}

.share-revoke-btn {
  margin-top: 12rpx;
  text-align: center;
  padding: 12rpx;
  border: 1rpx solid #d93025;
  border-radius: 12rpx;
  font-size: 24rpx;
  color: #d93025;
}

.share-revoke-btn.revoking {
  opacity: 0.5;
  border-color: #ccc;
  color: #ccc;
}

// No-token hint
.share-no-token-hint {
  margin-top: 8rpx;
  padding: 12rpx;
  background: #fff8e1;
  border-radius: 8rpx;

  text {
    font-size: 22rpx;
    color: #e6a23c;
    line-height: 1.5;
  }
}

// Share item action buttons
.share-item-actions {
  display: flex;
  gap: 12rpx;
  margin-top: 12rpx;
}

.share-action-btn {
  flex: 1;
  text-align: center;
  padding: 12rpx 8rpx;
  border: 1rpx solid #4A90D9;
  border-radius: 12rpx;
  font-size: 24rpx;
  color: #4A90D9;
}

.share-action-btn.danger {
  border-color: #d93025;
  color: #d93025;
}

.share-action-btn.revoking {
  opacity: 0.5;
}
</style>
