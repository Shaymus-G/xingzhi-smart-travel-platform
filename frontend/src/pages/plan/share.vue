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
type PageStatus = 'input' | 'loading' | 'loaded' | 'not_found' | 'network_error'

const pageStatus = ref<PageStatus>('loading')
const viewModel = ref<PublicShareViewModel | null>(null)
const errorMessage = ref('')
const token = ref('')
const inputToken = ref('')
const isSubmitting = ref(false)

// ========== Token 输入规范化 ==========

/**
 * 从用户输入中提取 share_token
 *
 * 支持格式：
 *   - 纯 Token：abc123def456
 *   - API 路径：/api/public/plan-shares/abc123def456
 *   - 完整 URL：https://example.com/#/pages/plan/share?token=abc123def456
 *
 * 不依赖 URL / URLSearchParams / window / document。
 */
function normalizeShareTokenInput(input: string): string | null {
  let text = input.trim()
  if (!text) return null

  // 包含 token= 参数 → 提取 token 值
  const tokenParamIdx = text.indexOf('token=')
  if (tokenParamIdx >= 0) {
    const after = text.slice(tokenParamIdx + 6) // 'token='.length
    // 截断到下一个 & 或 #
    const ampIdx = after.search(/[&#]/)
    text = ampIdx >= 0 ? after.slice(0, ampIdx) : after
    // 解码
    try { text = decodeURIComponent(text) } catch { /* keep raw */ }
    text = text.trim()
    if (text) return text
    return null
  }

  // 包含 /api/public/plan-shares/ → 提取最后一段
  const sharesIdx = text.indexOf('/api/public/plan-shares/')
  if (sharesIdx >= 0) {
    const after = text.slice(sharesIdx + '/api/public/plan-shares/'.length)
    // 截断到下一个 ? 或 #
    const qIdx = after.search(/[?#]/)
    const extracted = qIdx >= 0 ? after.slice(0, qIdx) : after
    const cleaned = extracted.trim().replace(/\/+$/, '')
    if (cleaned) return cleaned
    return null
  }

  // 纯 Token：无空格、无斜杠的字符串
  if (!text.includes(' ') && !text.includes('\n')) {
    return text
  }

  return null
}

// ========== 生命周期 ==========
onLoad((options: Record<string, string> | undefined) => {
  const rawToken = options?.token
  if (!rawToken || !rawToken.trim()) {
    pageStatus.value = 'input'
    return
  }
  token.value = rawToken.trim()
  void loadShare()
})

// ========== 数据加载 ==========
async function loadShare(): Promise<void> {
  if (!token.value) {
    pageStatus.value = 'input'
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

// ========== Token 提交 ==========

/** 用户点击"查看计划" */
function handleSubmitToken(): void {
  if (isSubmitting.value) return

  const normalized = normalizeShareTokenInput(inputToken.value)
  if (!normalized) {
    uni.showToast({ title: '分享 Token 格式不正确', icon: 'none' })
    return
  }

  isSubmitting.value = true
  token.value = normalized
  void loadShare().finally(() => {
    isSubmitting.value = false
  })
}

/** 重试 — 返回输入界面 */
function handleBackToInput(): void {
  token.value = ''
  inputToken.value = ''
  viewModel.value = null
  errorMessage.value = ''
  pageStatus.value = 'input'
}

// ========== Token 复制与遮罩 ==========

/** 遮罩 Token 用于页面显示 */
function maskShareToken(t: string): string {
  if (!t || t.length <= 12) return '已获取分享凭证'
  return t.slice(0, 4) + '****' + t.slice(-4)
}

/** 复制当前 Token 到剪贴板 */
function copyCurrentShareToken(): void {
  if (!token.value) return
  uni.setClipboardData({
    data: token.value,
    success: () => {
      uni.showToast({ title: '分享 Token 已复制', icon: 'success' })
    },
    fail: () => {
      uni.showToast({ title: '复制失败，请重试', icon: 'none' })
    },
  })
}
</script>

<template>
  <view class="share-page">
    <NavBar title="分享的旅行计划" :show-back="true" />

    <!-- 加载中 -->
    <view v-if="pageStatus === 'loading'" class="share-status">
      <text>加载中...</text>
    </view>

    <!-- Token 输入表单（无 token 参数时） -->
    <view v-else-if="pageStatus === 'input'" class="share-input-area">
      <view class="share-input-card">
        <text class="share-input-icon">🔗</text>
        <text class="share-input-title">查看分享的旅行计划</text>
        <text class="share-input-desc">输入分享 Token 查看他人分享的旅行计划</text>

        <input
          v-model="inputToken"
          class="share-input-field"
          placeholder="请输入分享 Token"
          placeholder-style="color:#ccc;"
          :disabled="isSubmitting"
          confirm-type="done"
          @confirm="handleSubmitToken"
        />

        <view
          class="share-input-btn"
          :class="{ disabled: !inputToken.trim() || isSubmitting }"
          @tap="handleSubmitToken"
        >
          <text>{{ isSubmitting ? '加载中...' : '查看计划' }}</text>
        </view>

        <text class="share-input-hint">分享 Token 由计划创建者提供</text>
        <text class="share-input-hint-secondary">支持粘贴 Token、分享链接或 API 地址</text>
      </view>
    </view>

    <!-- 不存在/已撤销/已过期 -->
    <view v-else-if="pageStatus === 'not_found'" class="share-status">
      <text class="share-error-icon">🔗</text>
      <text class="share-error-title">分享不存在或已失效</text>
      <text class="share-error-desc">该分享链接可能已被撤销、已过期或不存在。</text>
      <view class="share-action-row">
        <view class="share-retry-btn" @tap="handleBackToInput">
          <text>重新输入</text>
        </view>
      </view>
    </view>

    <!-- 网络错误 -->
    <view v-else-if="pageStatus === 'network_error'" class="share-status">
      <text class="share-error-icon">📡</text>
      <text class="share-error-title">网络异常</text>
      <text class="share-error-desc">{{ errorMessage || '请检查网络后重试' }}</text>
      <view class="share-action-row">
        <view class="share-retry-btn" @tap="loadShare">
          <text>重新加载</text>
        </view>
        <view class="share-retry-btn secondary" @tap="handleBackToInput">
          <text>重新输入</text>
        </view>
      </view>
    </view>

    <!-- 正常内容 -->
    <scroll-view v-else-if="viewModel" class="share-scroll" scroll-y>
      <view class="share-content">
      <!-- 基本信息 -->
      <view class="info-card">
        <text class="info-title">{{ viewModel.title }}</text>

        <!-- 分享凭证（遮罩显示 + 复制按钮） -->
        <view class="share-credential-row">
          <text class="share-credential-label">分享凭证：{{ maskShareToken(token) }}</text>
          <text class="share-credential-copy" @tap="copyCurrentShareToken">复制 Token</text>
        </view>

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
      </view><!-- /.share-content -->
    </scroll-view>
  </view>
</template>

<style lang="scss" scoped>
// ==================== 页面根容器 ====================
.share-page {
  min-height: 100vh;
  background: #f5f5f5;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

// ==================== scroll-view ====================
.share-scroll {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

// ==================== 统一内容容器（左右对称 32rpx） ====================
.share-content {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
  padding: 24rpx 32rpx 60rpx 32rpx;
}

// ==================== 状态页（loading / 错误 / 空状态） ====================
.share-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 160rpx 32rpx 0;
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;

  text {
    max-width: 100%;
  }
}

.share-action-row {
  display: flex;
  gap: 24rpx;
  margin-top: 32rpx;
  max-width: 100%;
  flex-wrap: wrap;
  justify-content: center;
}

.share-retry-btn.secondary {
  border-color: #ccc;
  color: #999;
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
  text-align: center;
  overflow-wrap: anywhere;
  word-break: break-word;
  max-width: 100%;
}

.share-error-desc {
  font-size: 26rpx;
  color: #999;
  text-align: center;
  line-height: 1.5;
  overflow-wrap: anywhere;
  word-break: break-word;
  max-width: 100%;
}

.share-retry-btn {
  margin-top: 32rpx;
  padding: 12rpx 40rpx;
  border: 1px solid #4A90D9;
  border-radius: 32rpx;
  font-size: 28rpx;
  color: #4A90D9;
}

// ==================== Token 输入区域 ====================
.share-input-area {
  display: flex;
  justify-content: center;
  padding: 80rpx 32rpx;
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
}

.share-input-card {
  width: 100%;
  max-width: 100%;
  background: #fff;
  border-radius: 24rpx;
  padding: 48rpx 40rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-sizing: border-box;
}

.share-input-icon {
  font-size: 72rpx;
  margin-bottom: 20rpx;
}

.share-input-title {
  font-size: 32rpx;
  font-weight: 700;
  color: #333;
  margin-bottom: 12rpx;
  text-align: center;
  overflow-wrap: anywhere;
  word-break: break-word;
  max-width: 100%;
}

.share-input-desc {
  font-size: 26rpx;
  color: #999;
  text-align: center;
  margin-bottom: 32rpx;
  line-height: 1.5;
  overflow-wrap: anywhere;
  word-break: break-word;
  max-width: 100%;
}

.share-input-field {
  width: 100%;
  max-width: 100%;
  height: 80rpx;
  background: #f8f8f8;
  border-radius: 12rpx;
  padding: 0 24rpx;
  font-size: 28rpx;
  box-sizing: border-box;
  margin-bottom: 24rpx;
}

.share-input-btn {
  width: 100%;
  max-width: 100%;
  height: 80rpx;
  background: #4A90D9;
  border-radius: 40rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20rpx;
  box-sizing: border-box;

  text {
    font-size: 30rpx;
    color: #fff;
  }
}

.share-input-btn.disabled {
  background: #ccc;
}

.share-input-hint {
  font-size: 24rpx;
  color: #bbb;
  text-align: center;
  line-height: 1.5;
  max-width: 100%;
  overflow-wrap: anywhere;
}

.share-input-hint-secondary {
  font-size: 22rpx;
  color: #ccc;
  text-align: center;
  margin-top: 4rpx;
  max-width: 100%;
  overflow-wrap: anywhere;
}

// ==================== 信息卡片 ====================
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
  overflow-wrap: anywhere;
  word-break: break-word;
}

// ===== 分享凭证行 =====
.share-credential-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12rpx 16rpx;
  background: #f8f8f8;
  border-radius: 10rpx;
  margin-bottom: 20rpx;
  gap: 12rpx;
}

.share-credential-label {
  font-size: 24rpx;
  color: #999;
  font-family: monospace;
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-all;
}

.share-credential-copy {
  font-size: 24rpx;
  color: #4A90D9;
  padding: 6rpx 16rpx;
  border: 1rpx solid #4A90D9;
  border-radius: 8rpx;
  flex-shrink: 0;
  white-space: nowrap;
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

.info-time-row {
  display: flex;
  gap: 32rpx;
  margin-top: 16rpx;
  padding-top: 16rpx;
  border-top: 1rpx solid #f0f0f0;
  flex-wrap: wrap;
}

.info-time {
  font-size: 24rpx;
  color: #bbb;
  overflow-wrap: anywhere;
}

// ==================== 段落标题 ====================
.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #333;
  display: block;
  margin-bottom: 16rpx;
  overflow-wrap: anywhere;
  word-break: break-word;
}

// ==================== 每日行程卡片 ====================
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
  gap: 16rpx;
  margin-bottom: 16rpx;
  min-width: 0;
  width: 100%;
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
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

// ==================== 时间线 ====================
.timeline {
  padding-left: 12rpx;
  min-width: 0;
}

.timeline-item {
  display: flex;
  gap: 16rpx;
  margin-bottom: 20rpx;
  min-width: 0;
  width: 100%;
  max-width: 100%;
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
  max-width: 100%;
  box-sizing: border-box;
}

.tl-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  min-width: 0;
  max-width: 100%;
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
  overflow-wrap: anywhere;
  word-break: break-word;
  max-width: 100%;
}

.tl-cost {
  font-size: 24rpx;
  color: #FF6B35;
  margin-top: 4rpx;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.tl-transport {
  font-size: 24rpx;
  color: #999;
  margin-top: 4rpx;
  overflow-wrap: anywhere;
  word-break: break-word;
  max-width: 100%;
}

// ==================== 餐饮 & 酒店 ====================
.meals-section, .hotel-section {
  margin-top: 16rpx;
  padding-top: 16rpx;
  border-top: 1rpx solid #f0f0f0;
  width: 100%;
  max-width: 100%;
}

.meals-title {
  font-size: 26rpx;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 8rpx;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.meal-item {
  font-size: 26rpx;
  color: #666;
  margin-bottom: 4rpx;
  overflow-wrap: anywhere;
  word-break: break-word;
  max-width: 100%;
}

.hotel-name {
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
  display: block;
  overflow-wrap: anywhere;
  word-break: break-word;
}

// ==================== Tips / 空状态卡片 ====================
.tips-card {
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
  line-height: 1.5;
  overflow-wrap: anywhere;
  word-break: break-word;
}

// ==================== 页脚 ====================
.share-footer {
  text-align: center;
  padding: 32rpx 0;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));

  text {
    display: block;
    margin-bottom: 8rpx;
    font-size: 24rpx;
    color: #bbb;
    overflow-wrap: anywhere;
    word-break: break-word;
  }
}
</style>
