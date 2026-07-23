<script setup lang="ts">
/**
 * 旅行计划列表页面
 */
import { ref, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'
import { getMyPlans } from '@/api/travel'
import type { TravelPlan } from '@/types/travel'

const plans = ref<TravelPlan[]>([])
const isLoading = ref(true)

onMounted(async () => {
  try {
    plans.value = await getMyPlans({ skip: 0, limit: 50 })
  } catch (_err) {
    // 加载失败保持空列表
  } finally {
    isLoading.value = false
  }
})

function goToDetail(id: number) {
  uni.navigateTo({ url: `/pages/plan/detail?id=${id}` })
}

function goToGenerate() {
  uni.navigateTo({ url: '/pages/plan/generate' })
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

    <!-- 加载中 -->
    <view v-if="isLoading" class="plan-empty">
      <text>加载中...</text>
    </view>

    <!-- 空状态 -->
    <view v-else-if="plans.length === 0" class="plan-empty">
      <text class="plan-empty-icon">📋</text>
      <text>暂无旅行计划</text>
      <text class="plan-empty-hint">点击上方按钮生成你的第一个 AI 旅行计划</text>
    </view>

    <!-- 计划列表 -->
    <scroll-view v-else class="plan-list" scroll-y>
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
        <text class="plan-date">{{ formatDate(plan.created_at) }}</text>
      </view>
    </scroll-view>
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

.plan-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
  font-size: 28rpx;
  color: #999;
}

.plan-empty-icon {
  font-size: 80rpx;
  margin-bottom: 24rpx;
}

.plan-empty-hint {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #bbb;
}

.plan-list {
  padding: 16rpx 32rpx;
}

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

.plan-date {
  font-size: 24rpx;
  color: #bbb;
}
</style>
