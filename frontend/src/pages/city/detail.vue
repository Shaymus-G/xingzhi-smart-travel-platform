<script setup lang="ts">
/**
 * 城市详情页面（骨架）
 * 展示城市信息 + 该城市的景点列表
 * 后续接入 getCityById(id) + getScenics({ city_id: id })
 */
import { ref, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'

const cityId = ref<number>(0)

onMounted(() => {
  // 从路由参数获取 cityId
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as any
  const id = currentPage?.options?.id
  cityId.value = Number(id) || 0
})
</script>

<template>
  <view class="city-detail-page">
    <NavBar title="城市详情" :show-back="true" />

    <!-- 城市信息骨架 -->
    <view class="city-header">
      <image class="city-cover" src="/static/logo.png" mode="aspectFill" />
      <view class="city-header-info">
        <text class="city-name">城市加载中...</text>
        <text class="city-desc">后续接入接口获取真实数据</text>
      </view>
    </view>

    <!-- 景点列表骨架 -->
    <view class="city-section">
      <text class="city-section-title">热门景点</text>
      <view class="city-empty">
        <text>景点列表将在此展示</text>
        <text class="city-empty-hint">（后续接入 getScenics 接口）</text>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.city-detail-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.city-header {
  position: relative;
}

.city-cover {
  width: 100%;
  height: 400rpx;
  background: #e0e0e0;
}

.city-header-info {
  padding: 24rpx 32rpx;
  background: #fff;
}

.city-name {
  font-size: 38rpx;
  font-weight: 700;
  color: #333;
  display: block;
}

.city-desc {
  font-size: 26rpx;
  color: #999;
  margin-top: 8rpx;
  display: block;
}

.city-section {
  margin-top: 16rpx;
  background: #fff;
  padding: 24rpx 32rpx;
}

.city-section-title {
  font-size: 30rpx;
  font-weight: 600;
  margin-bottom: 16rpx;
  display: block;
}

.city-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80rpx 0;
  font-size: 28rpx;
  color: #999;
}

.city-empty-hint {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #bbb;
}
</style>
