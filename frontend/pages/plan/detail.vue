<script setup lang="ts">
/**
 * 旅行计划详情页面 — 使用 plan_json 结构化渲染
 */
import { ref, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'
import { getPlanDetail } from '@/api/travel'
import type { TravelPlan } from '@/types/travel'

interface PlanJson {
  title?: string
  destination?: { name?: string; province?: string; city_id?: number }
  days?: number
  travelers?: number
  summary?: string | null
  budget?: {
    requested_total?: number | null
    estimated_total?: number
    breakdown?: {
      tickets?: number
      food?: number
      lodging?: number
      transport?: number
      other?: number
    }
  }
  itinerary?: DayPlanJson[]
  tips?: string[]
  assumptions?: string[]
}

interface DayPlanJson {
  day?: number
  theme?: string
  summary?: string | null
  weather_note?: string | null
  items?: ItemJson[]
  meals?: MealJson[]
  hotel?: HotelJson | null
  daily_estimated_cost?: number
}

interface ItemJson {
  period?: string
  start_time?: string | null
  end_time?: string | null
  resource_type?: string
  resource_id?: number | null
  name?: string
  address?: string | null
  duration_minutes?: number | null
  estimated_cost?: number
  reason?: string | null
  transport_to_next?: string | null
}

interface MealJson {
  period?: string
  name?: string
  estimated_cost?: number
}

interface HotelJson {
  name?: string
  address?: string | null
  estimated_cost?: number
}

const plan = ref<TravelPlan | null>(null)
const planJson = ref<PlanJson | null>(null)
const isLoading = ref(true)
const planId = ref(0)

onMounted(async () => {
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as any
  planId.value = Number(currentPage?.options?.id) || 0

  try {
    plan.value = await getPlanDetail(planId.value)
    planJson.value = plan.value.plan_json as PlanJson | null
  } catch (_err) {
    // error handled by request layer
  } finally {
    isLoading.value = false
  }
})

const PERIOD_LABELS: Record<string, string> = {
  morning: '上午',
  noon: '中午',
  afternoon: '下午',
  evening: '傍晚',
  night: '晚上',
}

const RTYPE_LABELS: Record<string, string> = {
  scenic_spot: '景点',
  restaurant: '餐厅',
  hotel: '酒店',
  general_activity: '活动',
}

function fmtCost(cost: number | undefined): string {
  if (cost === undefined || cost === null) return '--'
  if (cost === 0) return '免费'
  return `¥${cost}`
}

function fmtNum(n: number | undefined): string {
  if (n === undefined || n === null) return '--'
  return String(n)
}
</script>

<template>
  <view class="detail-page">
    <NavBar title="计划详情" :show-back="true" />

    <!-- 加载中 -->
    <view v-if="isLoading" class="detail-loading">
      <text>加载中...</text>
    </view>

    <scroll-view v-else-if="plan && planJson" class="detail-scroll" scroll-y>
      <!-- 标题和基本信息 -->
      <view class="info-card">
        <text class="info-title">{{ planJson.title || plan.title }}</text>
        <text class="info-summary" v-if="planJson.summary">{{ planJson.summary }}</text>

        <view class="info-grid">
          <view class="info-item">
            <text class="info-label">目的地</text>
            <text class="info-value">{{ plan.destination }}</text>
          </view>
          <view class="info-item">
            <text class="info-label">天数</text>
            <text class="info-value">{{ plan.days }} 天</text>
          </view>
          <view class="info-item" v-if="planJson.travelers && planJson.travelers > 1">
            <text class="info-label">人数</text>
            <text class="info-value">{{ planJson.travelers }} 人</text>
          </view>
          <view class="info-item" v-if="plan.budget">
            <text class="info-label">预算</text>
            <text class="info-value">¥{{ plan.budget }}</text>
          </view>
          <view class="info-item" v-if="planJson.budget?.estimated_total">
            <text class="info-label">预估费用</text>
            <text class="info-value highlight">¥{{ planJson.budget.estimated_total }}</text>
          </view>
        </view>
      </view>

      <!-- 每日行程 -->
      <view class="itinerary-section" v-if="planJson.itinerary">
        <text class="section-title">行程安排</text>

        <view v-for="(day, di) in planJson.itinerary" :key="di" class="day-card">
          <view class="day-header">
            <text class="day-num">第 {{ day.day }} 天</text>
            <text class="day-theme" v-if="day.theme">{{ day.theme }}</text>
          </view>

          <text class="day-summary" v-if="day.summary">{{ day.summary }}</text>
          <text class="day-weather" v-if="day.weather_note">🌤️ {{ day.weather_note }}</text>

          <!-- 行程项目 -->
          <view class="timeline" v-if="day.items">
            <view v-for="(item, ii) in day.items" :key="ii" class="timeline-item">
              <view class="timeline-dot" :class="item.resource_type" />
              <view class="timeline-content">
                <view class="tl-header">
                  <text class="tl-name">{{ item.name }}</text>
                  <text class="tl-type">{{ RTYPE_LABELS[item.resource_type || ''] || item.resource_type }}</text>
                </view>
                <text class="tl-meta" v-if="item.start_time || item.end_time">
                  ⏰ {{ item.start_time || '?' }} - {{ item.end_time || '?' }}
                </text>
                <text class="tl-meta" v-if="item.address">📍 {{ item.address }}</text>
                <text class="tl-meta" v-if="item.duration_minutes">
                  ⏱️ {{ item.duration_minutes }} 分钟
                </text>
                <text class="tl-cost" v-if="item.estimated_cost !== undefined">
                  💰 {{ fmtCost(item.estimated_cost) }}
                </text>
                <text class="tl-reason" v-if="item.reason">💡 {{ item.reason }}</text>
                <text class="tl-transport" v-if="item.transport_to_next">
                  🚗 {{ item.transport_to_next }}
                </text>
              </view>
            </view>
          </view>

          <!-- 用餐 -->
          <view class="meals-section" v-if="day.meals && day.meals.length > 0">
            <text class="meals-title">🍜 用餐</text>
            <view v-for="(meal, mi) in day.meals" :key="mi" class="meal-item">
              <text>{{ PERIOD_LABELS[meal.period || ''] || meal.period }}：{{ meal.name }}</text>
              <text v-if="meal.estimated_cost"> {{ fmtCost(meal.estimated_cost) }}</text>
            </view>
          </view>

          <!-- 住宿 -->
          <view class="hotel-section" v-if="day.hotel">
            <text class="meals-title">🏨 住宿</text>
            <text class="hotel-name">{{ day.hotel.name }}</text>
            <text class="tl-meta" v-if="day.hotel.address">📍 {{ day.hotel.address }}</text>
            <text class="tl-cost">💰 {{ fmtCost(day.hotel.estimated_cost) }}</text>
          </view>

          <!-- 当日费用 -->
          <view class="day-cost" v-if="day.daily_estimated_cost">
            <text>本日预估：{{ fmtCost(day.daily_estimated_cost) }}</text>
          </view>
        </view>
      </view>

      <!-- 预算明细 -->
      <view class="budget-card" v-if="planJson.budget?.breakdown">
        <text class="section-title">预算明细</text>
        <view class="budget-row">
          <text>门票</text><text>{{ fmtCost(planJson.budget.breakdown.tickets) }}</text>
        </view>
        <view class="budget-row">
          <text>餐饮</text><text>{{ fmtCost(planJson.budget.breakdown.food) }}</text>
        </view>
        <view class="budget-row">
          <text>住宿</text><text>{{ fmtCost(planJson.budget.breakdown.lodging) }}</text>
        </view>
        <view class="budget-row">
          <text>交通</text><text>{{ fmtCost(planJson.budget.breakdown.transport) }}</text>
        </view>
        <view class="budget-row">
          <text>其他</text><text>{{ fmtCost(planJson.budget.breakdown.other) }}</text>
        </view>
        <view class="budget-row total">
          <text>合计</text><text>{{ fmtCost(planJson.budget.estimated_total) }}</text>
        </view>
      </view>

      <!-- 旅行贴士 -->
      <view class="tips-card" v-if="planJson.tips && planJson.tips.length > 0">
        <text class="section-title">旅行贴士</text>
        <text v-for="(tip, ti) in planJson.tips" :key="ti" class="tip-item">• {{ tip }}</text>
      </view>

      <!-- 假设与说明 -->
      <view class="assumptions-card" v-if="planJson.assumptions && planJson.assumptions.length > 0">
        <text class="section-title">假设与数据说明</text>
        <text v-for="(a, ai) in planJson.assumptions" :key="ai" class="tip-item">• {{ a }}</text>
      </view>

      <!-- 页脚 -->
      <view class="detail-footer">
        <text>本计划由行知 AI 助手生成</text>
        <text>实际价格、开放时间和天气可能变化，出行前请再次确认</text>
      </view>
    </scroll-view>

    <!-- 加载失败 -->
    <view v-else-if="!isLoading" class="detail-empty">
      <text>计划加载失败</text>
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
</style>
