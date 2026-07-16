<script setup lang="ts">
/**
 * 景点详情页面（骨架）
 * 后续接入 getScenicById(id) + getReviews({ target_type: 'scenic_spot', target_id: id })
 */
import { ref, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'

const scenicId = ref<number>(0)

onMounted(() => {
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as any
  scenicId.value = Number(currentPage?.options?.id) || 0
})

const isFavorited = ref(false)

function toggleFavorite() {
  isFavorited.value = !isFavorited.value
  const msg = isFavorited.value ? '已收藏' : '已取消收藏'
  // 后续接入 addFavorite / removeFavorite 接口
  uni.showToast({ title: msg, icon: 'none' })
}
</script>

<template>
  <view class="scenic-detail-page">
    <NavBar title="景点详情" :show-back="true" />

    <!-- 景点图片 -->
    <image class="scenic-cover" src="/static/logo.png" mode="aspectFill" />

    <!-- 基本信息骨架 -->
    <view class="scenic-info">
      <view class="scenic-header">
        <text class="scenic-name">景点加载中...</text>
        <view class="scenic-favorite" @tap="toggleFavorite">
          <text>{{ isFavorited ? '❤️' : '🤍' }}</text>
        </view>
      </view>
      <view class="scenic-meta">
        <text class="scenic-meta-item">★ --</text>
        <text class="scenic-meta-item">¥ --</text>
        <text class="scenic-meta-item">--</text>
      </view>
      <text class="scenic-desc">后续接入后端接口获取真实景点数据</text>
    </view>

    <!-- 评论骨架 -->
    <view class="scenic-section">
      <text class="scenic-section-title">游客评论</text>
      <view class="scenic-empty">
        <text>评论列表将在此展示</text>
        <text class="scenic-empty-hint">（后续接入 getReviews 接口）</text>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.scenic-detail-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.scenic-cover {
  width: 100%;
  height: 420rpx;
  background: #e0e0e0;
}

.scenic-info {
  background: #fff;
  padding: 24rpx 32rpx;
}

.scenic-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.scenic-name {
  font-size: 38rpx;
  font-weight: 700;
  color: #333;
}

.scenic-favorite {
  font-size: 48rpx;
}

.scenic-meta {
  display: flex;
  gap: 32rpx;
  margin: 16rpx 0;
}

.scenic-meta-item {
  font-size: 26rpx;
  color: #666;
}

.scenic-desc {
  font-size: 26rpx;
  color: #999;
  line-height: 1.6;
}

.scenic-section {
  margin-top: 16rpx;
  background: #fff;
  padding: 24rpx 32rpx;
}

.scenic-section-title {
  font-size: 30rpx;
  font-weight: 600;
  margin-bottom: 16rpx;
  display: block;
}

.scenic-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80rpx 0;
  font-size: 28rpx;
  color: #999;
}

.scenic-empty-hint {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #bbb;
}
</style>
