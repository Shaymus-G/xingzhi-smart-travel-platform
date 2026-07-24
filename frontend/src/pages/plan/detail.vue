<script setup lang="ts">
/**
 * 旅行计划详情页面 — 使用 normalizer 安全渲染 plan_json
 */
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
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

// ========== 生命周期 ==========
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
            <text class="day-num">第 {{ day.day }} 天</text>
            <text class="day-theme" v-if="day.theme">{{ day.theme }}</text>
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

                <!-- 实时路线 -->
                <TransitRoutePanel
                  v-if="getTransitSegment(day.items, ii)"
                  :origin-type="getTransitSegment(day.items, ii)!.originType"
                  :origin-id="getTransitSegment(day.items, ii)!.originId"
                  :origin-name="getTransitSegment(day.items, ii)!.originName"
                  :destination-type="getTransitSegment(day.items, ii)!.destinationType"
                  :destination-id="getTransitSegment(day.items, ii)!.destinationId"
                  :destination-name="getTransitSegment(day.items, ii)!.destinationName"
                  :city="transitCity()"
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
            <text class="tl-meta" v-if="day.hotel.address">📍 {{ day.hotel.address }}</text>
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
  </view>
</template>

<style lang="scss" scoped>
.detail-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.detail-loading, .detail-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-top: 200rpx;
  font-size: 28rpx;
  color: #999;
}

.detail-scroll {
  padding: 24rpx 32rpx;
  padding-bottom: 60rpx;
}

// Info card
.info-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
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
}

.info-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
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
}

.day-header {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 12rpx;
}

.day-num {
  background: #4A90D9;
  color: #fff;
  font-size: 24rpx;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
}

.day-theme {
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
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
}

.tl-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.tl-name {
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
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
}

.tl-meta {
  font-size: 24rpx;
  color: #999;
  display: block;
  margin-top: 4rpx;
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
}

.budget-row {
  display: flex;
  justify-content: space-between;
  font-size: 28rpx;
  color: #333;
  padding: 8rpx 0;
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
}

.tip-item {
  font-size: 26rpx;
  color: #666;
  display: block;
  padding: 6rpx 0;
  line-height: 1.5;
}

// Footer
.detail-footer {
  text-align: center;
  padding: 32rpx 0;
  font-size: 24rpx;
  color: #bbb;

  text {
    display: block;
    margin-bottom: 8rpx;
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

  .detail-action-btn {
    flex: 1;
  }
}
</style>
