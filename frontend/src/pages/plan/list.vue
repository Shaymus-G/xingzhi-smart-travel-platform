<script setup lang="ts">
/**
 * 旅行计划列表页面 — 分页 / 下拉刷新 / 删除
 */
import { ref, computed } from 'vue'
import { onShow, onPullDownRefresh, onReachBottom } from '@dcloudio/uni-app'
import NavBar from '@/components/NavBar.vue'
import { getMyPlans, deletePlan } from '@/api/travel'
import type { TravelPlan } from '@/types/travel'

// ========== 常量 ==========
const PAGE_SIZE = 20

// ========== 列表状态 ==========
const plans = ref<TravelPlan[]>([])
const isInitialLoading = ref(true)     // 初始显示加载中；注意：isInitialLoading 不在 isListBusy 中
const isRefreshing = ref(false)
const isLoadingMore = ref(false)
const hasMore = ref(true)
const loadError = ref<string | null>(null)
const deletingIds = ref<Set<number>>(new Set())

// isListBusy 只包含真正的"请求进行中"状态，不包含 isInitialLoading
// （isInitialLoading 在 refreshPlans 内部设置，如果放入 isListBusy 会导致首次调用被拦截）
const isListBusy = computed(
  () => isRefreshing.value || isLoadingMore.value,
)

// ========== 生命周期 ==========

onShow(() => {
  if (import.meta.env.DEV) {
    console.log('[plan-list] onShow', { isInitialLoading: isInitialLoading.value, isListBusy: isListBusy.value, plansLen: plans.value.length })
  }
  void refreshPlans('show')
})

onPullDownRefresh(() => {
  void refreshPlans('pull-down')
})

onReachBottom(() => {
  void loadMorePlans()
})

// ========== 数据加载 ==========

async function refreshPlans(source: 'show' | 'pull-down' | 'retry'): Promise<void> {
  // 列表请求互斥（isRefreshing / isLoadingMore，不含 isInitialLoading）
  if (isListBusy.value) {
    if (import.meta.env.DEV) {
      console.log('[plan-list] refreshPlans blocked by isListBusy', { source })
    }
    if (source === 'pull-down') uni.stopPullDownRefresh()
    return
  }

  if (import.meta.env.DEV) {
    console.log('[plan-list] refreshPlans executing', { source })
  }

  if (plans.value.length === 0) {
    isInitialLoading.value = true
  } else {
    isRefreshing.value = true
  }

  try {
    const result = await getMyPlans({ skip: 0, limit: PAGE_SIZE })
    plans.value = result || []
    loadError.value = null
    hasMore.value = (result && result.length === PAGE_SIZE) ?? false
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '加载失败'
    if (plans.value.length === 0) {
      loadError.value = msg
    }
    // 有旧数据时保留，只轻量提示
  } finally {
    isInitialLoading.value = false
    isRefreshing.value = false
    if (source === 'pull-down') uni.stopPullDownRefresh()
  }
}

async function loadMorePlans(): Promise<void> {
  if (!hasMore.value || isListBusy.value || loadError.value) return

  isLoadingMore.value = true

  try {
    const result = await getMyPlans({ skip: plans.value.length, limit: PAGE_SIZE })
    if (!result || result.length === 0) {
      hasMore.value = false
      return
    }

    // 按 ID 去重
    const existingIds = new Set(plans.value.map(p => p.id))
    const uniqueNew = result.filter(p => !existingIds.has(p.id))
    plans.value.push(...uniqueNew)

    hasMore.value = result.length === PAGE_SIZE
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '加载失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    isLoadingMore.value = false
  }
}

// ========== 删除 ==========

async function handleDelete(plan: TravelPlan): Promise<void> {
  if (deletingIds.value.has(plan.id)) return

  const modalRes = await uni.showModal({
    title: '删除计划',
    content: `确定删除"${plan.title}"吗？删除后无法恢复。`,
    confirmText: '删除',
    confirmColor: '#d93025',
  })

  if (!modalRes.confirm) return

  // 标记删除中
  const newSet = new Set(deletingIds.value)
  newSet.add(plan.id)
  deletingIds.value = newSet

  try {
    await deletePlan(plan.id)
    plans.value = plans.value.filter(p => p.id !== plan.id)
    uni.showToast({ title: '已删除', icon: 'success' })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '删除失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    const newSet2 = new Set(deletingIds.value)
    newSet2.delete(plan.id)
    deletingIds.value = newSet2
  }
}

// ========== 导航 ==========

function goToDetail(id: number): void {
  uni.navigateTo({ url: `/pages/plan/detail?id=${id}` })
}

function goToGenerate(): void {
  uni.navigateTo({ url: '/pages/plan/generate' })
}

function goToViewShare(): void {
  uni.navigateTo({ url: '/pages/plan/share' })
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  return dateStr.slice(0, 10)
}
</script>

<template>
  <view class="plan-list-page">
    <NavBar title="旅行计划" />

    <!-- 生成入口 -->
    <view class="generate-entry" @tap="goToGenerate">
      <text class="generate-icon">+</text>
      <text>AI 生成新计划</text>
    </view>

    <!-- 查看分享入口 -->
    <view class="view-share-entry" @tap="goToViewShare">
      <text class="view-share-icon">🔗</text>
      <text>查看分享计划</text>
    </view>

    <!-- 初始加载中 -->
    <view v-if="isInitialLoading" class="plan-status">
      <text class="plan-status-text">加载中...</text>
    </view>

    <!-- 初始加载错误 -->
    <view v-else-if="loadError && plans.length === 0" class="plan-status plan-status-error">
      <text class="plan-status-text">{{ loadError }}</text>
      <view class="plan-retry-btn" @tap="refreshPlans('retry')">
        <text>重新加载</text>
      </view>
    </view>

    <!-- 空列表 -->
    <view v-else-if="!isInitialLoading && plans.length === 0 && !loadError" class="plan-status">
      <text class="plan-empty-icon">📋</text>
      <text class="plan-status-text">暂无旅行计划</text>
      <text class="plan-hint">点击上方按钮生成你的第一个 AI 旅行计划</text>
    </view>

    <!-- 正常列表 -->
    <view v-else class="plan-list">
      <view
        v-for="plan in plans"
        :key="plan.id"
        class="plan-card"
        @tap="goToDetail(plan.id)"
      >
        <view class="plan-card-header">
          <text class="plan-title">{{ plan.title }}</text>
          <text class="plan-arrow">→</text>
        </view>
        <view class="plan-meta">
          <text>{{ plan.destination }} · {{ plan.days }} 天</text>
          <text v-if="plan.budget"> · ¥{{ plan.budget }}</text>
        </view>
        <view class="plan-footer">
          <text class="plan-date">{{ formatDate(plan.created_at) }}</text>
          <view
            class="plan-delete-btn"
            :class="{ deleting: deletingIds.has(plan.id) }"
            @tap.stop="handleDelete(plan)"
          >
            <text>{{ deletingIds.has(plan.id) ? '删除中...' : '删除' }}</text>
          </view>
        </view>
      </view>

      <!-- 加载更多 -->
      <view v-if="isLoadingMore" class="plan-status plan-list-footer">
        <text class="plan-status-text">加载更多...</text>
      </view>

      <!-- 没有更多 -->
      <view v-else-if="!hasMore && plans.length > 0" class="plan-status plan-list-footer">
        <text class="plan-status-text" style="color:#bbb;">— 没有更多 —</text>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.plan-list-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.generate-entry {
  margin: 24rpx 32rpx;
  padding: 24rpx;
  background: #4A90D9;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  font-size: 30rpx;
  color: #fff;
  font-weight: 600;
}

.generate-icon {
  font-size: 40rpx;
  line-height: 1;
}

// View share entry
.view-share-entry {
  margin: 0 32rpx 16rpx;
  padding: 20rpx 24rpx;
  background: #fff;
  border: 1rpx solid #4A90D9;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  font-size: 26rpx;
  color: #4A90D9;
}

.view-share-icon {
  font-size: 32rpx;
}

// Status
.plan-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.plan-status-text {
  font-size: 28rpx;
  color: #999;
}

.plan-status-error .plan-status-text {
  color: #d93025;
}

.plan-retry-btn {
  margin-top: 24rpx;
  padding: 12rpx 40rpx;
  border: 1px solid #4A90D9;
  border-radius: 32rpx;
  font-size: 28rpx;
  color: #4A90D9;
}

.plan-empty-icon {
  font-size: 80rpx;
  margin-bottom: 24rpx;
}

.plan-hint {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #bbb;
}

// List
.plan-list {
  padding: 16rpx 32rpx;
}

.plan-list-footer {
  padding-top: 24rpx;
  padding-bottom: 32rpx;
}

// Card
.plan-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
}

.plan-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12rpx;
}

.plan-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #333;
  flex: 1;
}

.plan-arrow {
  font-size: 32rpx;
  color: #ccc;
}

.plan-meta {
  font-size: 26rpx;
  color: #666;
  margin-bottom: 8rpx;
}

.plan-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.plan-date {
  font-size: 24rpx;
  color: #bbb;
}

// Delete
.plan-delete-btn {
  padding: 6rpx 20rpx;
  border: 1px solid #d93025;
  border-radius: 24rpx;
  font-size: 22rpx;
  color: #d93025;
}

.plan-delete-btn.deleting {
  opacity: 0.5;
  border-color: #ccc;
  color: #ccc;
}
</style>
