<script setup lang="ts">
/**
 * 公开分享计划查看页面 — 无需登录
 *
 * 通过 URL 参数 token 读取分享内容。
 * 不携带 Authorization，不触发 401 跳转。
 */
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import NavBar from '@/components/NavBar.vue'
import { getPublicPlanShare } from '@/api/plan-share'
import { normalizeShareSnapshot } from '@/utils/plan-share-normalizer'
import type { PublicShareViewModel, ShareDayViewModel } from '@/utils/plan-share-normalizer'

// ========== 常量 ==========
const PERIOD_LABELS_MAP: Record<string, string> = {
  morning: '上午',
  noon: '中午',
  afternoon: '下午',
  evening: '傍晚',
  night: '晚上',
}

function periodLabel(p: string): string {
  return PERIOD_LABELS_MAP[p] || p
}

function fmtCostLocal(cost: number | null | undefined): string {
  if (cost === undefined || cost === null) return '--'
  if (cost === 0) return '免费'
  return `¥${cost}`
}

function fmtDateOnly(dateStr: string): string {
  if (!dateStr) return '--'
  return dateStr.slice(0, 16).replace('T', ' ')
}

// ========== 状态 ==========
type PageStatus = 'loading' | 'loaded' | 'not_found' | 'network_error' | 'invalid'

const pageStatus = ref<PageStatus>('loading')
const viewModel = ref<PublicShareViewModel | null>(null)
const errorMessage = ref('')
const token = ref('')

// ========== 生命周期 ==========
onLoad((options: Record<string, string> | undefined) => {
  const rawToken = options?.token
  if (!rawToken || !rawToken.trim()) {
    pageStatus.value = 'invalid'
    errorMessage.value = '缺少分享令牌'
    return
  }
  token.value = rawToken.trim()
  void loadShare()
})

// ========== 数据加载 ==========
async function loadShare(): Promise<void> {
  if (!token.value) {
    pageStatus.value = 'invalid'
    return
  }

  pageStatus.value = 'loading'

  const result = await getPublicPlanShare(token.value)

  if (!result.data) {
    const err = result.error || ''
    if (err.includes('不存在') || err.includes('已过期') || err.includes('not found')) {
      pageStatus.value = 'not_found'
    } else if (err.includes('网络') || err.includes('network') || err.includes('超时')) {
      pageStatus.value = 'network_error'
      errorMessage.value = err
    } else {
      pageStatus.value = 'not_found'
      errorMessage.value = err
    }
    return
  }

  const normalized = normalizeShareSnapshot(result.data)
  if (!normalized.data) {
    pageStatus.value = 'not_found'
    errorMessage.value = normalized.error || '分享内容无法解析'
    return
  }

  viewModel.value = normalized.data
  pageStatus.value = 'loaded'
}
</script>

<template>
  <view class="share-page">
    <NavBar title="分享的旅行计划" :show-back="true" />

    <!-- 加载中 -->
    <view v-if="pageStatus === 'loading'" class="share-status">
      <text>加载中...</text>
    </view>

    <!-- 缺少令牌 -->
    <view v-else-if="pageStatus === 'invalid'" class="share-status">
      <text class="share-error-icon">⚠️</text>
      <text class="share-error-title">无效的分享链接</text>
      <text class="share-error-desc">链接缺少分享令牌，无法查看计划内容。</text>
    </view>

    <!-- 不存在/已撤销/已过期 -->
    <view v-else-if="pageStatus === 'not_found'" class="share-status">
      <text class="share-error-icon">🔗</text>
      <text class="share-error-title">分享不存在或已失效</text>
      <text class="share-error-desc">该分享链接可能已被撤销、已过期或不存在。</text>
    </view>

    <!-- 网络错误 -->
    <view v-else-if="pageStatus === 'network_error'" class="share-status">
      <text class="share-error-icon">📡</text>
      <text class="share-error-title">网络异常</text>
      <text class="share-error-desc">{{ errorMessage || '请检查网络后重试' }}</text>
      <view class="share-retry-btn" @tap="loadShare">
        <text>重新加载</text>
      </view>
    </view>

    <!-- 正常内容 -->
    <scroll-view v-else-if="viewModel" class="share-scroll" scroll-y>
      <!-- 基本信息 -->
      <view class="info-card">
        <text class="info-title">{{ viewModel.title }}</text>

        <view class="info-grid">
          <view class="info-item">
            <text class="info-label">目的地</text>
            <text class="info-value">{{ viewModel.destination }}</text>
          </view>
          <view class="info-item">
            <text class="info-label">天数</text>
            <text class="info-value">{{ viewModel.days }} 天</text>
          </view>
          <view class="info-item" v-if="viewModel.hasBudget">
            <text class="info-label">预算</text>
            <text class="info-value">¥{{ viewModel.budget }}</text>
          </view>
        </view>

        <view class="info-time-row" v-if="viewModel.createdAt || viewModel.expiresAt">
          <text v-if="viewModel.createdAt" class="info-time">创建：{{ fmtDateOnly(viewModel.createdAt) }}</text>
          <text v-if="viewModel.expiresAt" class="info-time">过期：{{ fmtDateOnly(viewModel.expiresAt) }}</text>
        </view>
      </view>

      <!-- 每日行程 -->
      <view class="itinerary-section" v-if="viewModel.hasItinerary && viewModel.itinerary">
        <text class="section-title">行程安排</text>

        <view v-for="(day, di) in viewModel.itinerary" :key="di" class="day-card">
          <view class="day-header">
            <text class="day-num">第 {{ day.day }} 天</text>
            <text class="day-theme" v-if="day.theme">{{ day.theme }}</text>
          </view>

          <!-- 行程项目 -->
          <view class="timeline" v-if="day.items.length > 0">
            <view v-for="(item, ii) in day.items" :key="ii" class="timeline-item">
              <view class="timeline-dot" />
              <view class="timeline-content">
                <view class="tl-header">
                  <text class="tl-name">{{ item.name }}</text>
                  <text class="tl-period">{{ periodLabel(item.period) }}</text>
                </view>
                <text class="tl-meta" v-if="item.address">📍 {{ item.address }}</text>
                <text class="tl-meta" v-if="item.durationMinutes !== null">
                  ⏱️ {{ item.durationMinutes }} 分钟
                </text>
                <text class="tl-cost" v-if="item.estimatedCost !== null">
                  💰 {{ fmtCostLocal(item.estimatedCost) }}
                </text>
                <text class="tl-transport" v-if="item.transportToNext">
                  🚗 {{ item.transportToNext }}
                </text>
              </view>
            </view>
          </view>

          <!-- 餐饮 -->
          <view class="meals-section" v-if="day.meals.length > 0">
            <text class="meals-title">🍜 用餐</text>
            <view v-for="(meal, mi) in day.meals" :key="mi" class="meal-item">
              <text>{{ periodLabel(meal.period) }}：{{ meal.name }}</text>
              <text v-if="meal.estimatedCost !== null"> {{ fmtCostLocal(meal.estimatedCost) }}</text>
            </view>
          </view>

          <!-- 住宿 -->
          <view class="hotel-section" v-if="day.hotel">
            <text class="meals-title">🏨 住宿</text>
            <text class="hotel-name">{{ day.hotel.name }}</text>
            <text class="tl-meta" v-if="day.hotel.address">📍 {{ day.hotel.address }}</text>
            <text class="tl-cost" v-if="day.hotel.estimatedCost !== null">
              💰 {{ fmtCostLocal(day.hotel.estimatedCost) }}
            </text>
          </view>
        </view>
      </view>

      <!-- 无行程详情 -->
      <view v-else class="tips-card">
        <text class="tip-item">该分享暂未包含详细行程</text>
      </view>

      <!-- 页脚 -->
      <view class="share-footer">
        <text>本计划由行知 AI 助手生成</text>
        <text>实际价格、开放时间和天气可能变化，出行前请再次确认</text>
        <text>由"行知"智慧文旅生成</text>
      </view>
    </scroll-view>
  </view>
</template>

<style lang="scss" scoped>
.share-page {
  min-height: 100vh;
  background: #f5f5f5;
}

// Status
.share-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
  padding-left: 48rpx;
  padding-right: 48rpx;
}

.share-error-icon {
  font-size: 80rpx;
  margin-bottom: 24rpx;
}

.share-error-title {
  font-size: 32rpx;
  font-weight: 700;
  color: #333;
  margin-bottom: 16rpx;
}

.share-error-desc {
  font-size: 26rpx;
  color: #999;
  text-align: center;
  line-height: 1.5;
}

.share-retry-btn {
  margin-top: 32rpx;
  padding: 12rpx 40rpx;
  border: 1px solid #4A90D9;
  border-radius: 32rpx;
  font-size: 28rpx;
  color: #4A90D9;
}

// Scroll
.share-scroll {
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
  margin-bottom: 20rpx;
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

.info-time-row {
  display: flex;
  gap: 32rpx;
  margin-top: 16rpx;
  padding-top: 16rpx;
  border-top: 1rpx solid #f0f0f0;
}

.info-time {
  font-size: 24rpx;
  color: #bbb;
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
  margin-bottom: 16rpx;
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
  background: #4A90D9;
}

.timeline-content {
  flex: 1;
  min-width: 0;
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

.tl-period {
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

.tl-cost {
  font-size: 24rpx;
  color: #FF6B35;
  margin-top: 4rpx;
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

// Tips
.tips-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.tip-item {
  font-size: 26rpx;
  color: #666;
  display: block;
  line-height: 1.5;
}

// Footer
.share-footer {
  text-align: center;
  padding: 32rpx 0;

  text {
    display: block;
    margin-bottom: 8rpx;
    font-size: 24rpx;
    color: #bbb;
  }
}
</style>
