<script setup lang="ts">
/**
 * 旅行计划详情页面（骨架）
 * 后续接入 getPlanById(id) 接口
 */
import { ref, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'

const planId = ref<number>(0)

onMounted(() => {
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as any
  planId.value = Number(currentPage?.options?.id) || 0
})
</script>

<template>
  <view class="plan-detail-page">
    <NavBar title="计划详情" :show-back="true" />

    <view class="plan-info">
      <text class="plan-title">计划加载中...</text>
      <text class="plan-meta">目的地：-- | 天数：-- 天</text>
      <text class="plan-budget">预算：¥ --</text>
    </view>

    <view class="plan-content">
      <text class="plan-section-title">行程安排</text>
      <view class="plan-empty">
        <text>详细行程将在后续接入后端接口后展示</text>
        <text class="plan-empty-hint">（支持 Markdown 渲染）</text>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.plan-detail-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.plan-info {
  background: #fff;
  padding: 24rpx 32rpx;
}

.plan-title {
  font-size: 36rpx;
  font-weight: 700;
  color: #333;
  display: block;
  margin-bottom: 16rpx;
}

.plan-meta {
  font-size: 26rpx;
  color: #666;
  display: block;
}

.plan-budget {
  font-size: 28rpx;
  color: #FF6B35;
  font-weight: 600;
  margin-top: 8rpx;
  display: block;
}

.plan-content {
  margin-top: 16rpx;
  background: #fff;
  padding: 24rpx 32rpx;
}

.plan-section-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 16rpx;
}

.plan-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80rpx 0;
  font-size: 28rpx;
  color: #999;
}

.plan-empty-hint {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #bbb;
}
</style>
