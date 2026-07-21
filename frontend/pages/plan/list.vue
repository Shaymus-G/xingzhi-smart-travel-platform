<script setup lang="ts">
/**
 * 旅行计划列表页面（骨架）
 * 后续接入 getMyPlans() 接口
 */
import { ref } from 'vue'
import NavBar from '@/components/NavBar.vue'

const plans = ref<Array<{ id: number; title: string; destination: string; days: number; created_at: string }>>([])
</script>

<template>
  <view class="plan-list-page">
    <NavBar title="旅行计划" />

    <view class="plan-empty">
      <text class="plan-empty-icon">📋</text>
      <text>暂无旅行计划</text>
      <text class="plan-empty-hint">后续接入 AI 生成旅行计划功能</text>
    </view>

    <!-- 骨架列表（后续取消注释并接入真实数据） -->
    <!--
    <scroll-view class="plan-list" scroll-y>
      <view v-for="plan in plans" :key="plan.id" class="plan-card"
        @tap="uni.navigateTo({ url: '/pages/plan/detail?id=' + plan.id })">
        <text class="plan-title">{{ plan.title }}</text>
        <text class="plan-meta">{{ plan.destination }} · {{ plan.days }}天</text>
      </view>
    </scroll-view>
    -->
  </view>
</template>

<style lang="scss" scoped>
.plan-list-page {
  min-height: 100vh;
  background: #f5f5f5;
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
</style>
