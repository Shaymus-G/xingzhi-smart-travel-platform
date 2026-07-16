<script setup lang="ts">
/**
 * 首页（城市列表）— 骨架
 * 后续接入 getCities() 接口
 */
import { ref } from 'vue'
import NavBar from '@/components/NavBar.vue'

const cityList = ref<Array<{ id: number; name: string; province: string; level: string; cover_image: string; description: string }>>([])
const selectedLevel = ref('')

/** 骨架数据 */
const skeletonCities = [
  { id: 1, name: '北京', province: '北京', level: '热门', cover_image: '', description: '加载中...' },
]

/** 跳转到城市详情 */
function goCityDetail(id: number) {
  uni.navigateTo({ url: `/pages/city/detail?id=${id}` })
}
</script>

<template>
  <view class="home-page">
    <NavBar title="行知 · 发现城市" />

    <!-- 城市等级筛选 tab -->
    <view class="home-tabs">
      <view
        v-for="tab in ['全部', '热门', '普通', '小众']"
        :key="tab"
        class="home-tab"
        :class="{ active: (tab === '全部' ? '' : tab) === selectedLevel }"
        @tap="selectedLevel = tab === '全部' ? '' : tab"
      >
        {{ tab }}
      </view>
    </view>

    <!-- 城市列表（骨架占位） -->
    <scroll-view class="home-list" scroll-y enhanced :show-scrollbar="false">
      <view
        v-for="city in skeletonCities"
        :key="city.id"
        class="home-card"
        @tap="goCityDetail(city.id)"
      >
        <image class="home-card-image" src="/static/logo.png" mode="aspectFill" />
        <view class="home-card-info">
          <text class="home-card-name">{{ city.name }}</text>
          <text class="home-card-level">{{ city.level }}</text>
        </view>
      </view>

      <!-- 空状态 -->
      <view v-if="!skeletonCities.length" class="home-empty">
        <text>暂无城市数据</text>
        <text class="home-empty-hint">后续接入后端接口自动显示</text>
      </view>
    </scroll-view>
  </view>
</template>

<style lang="scss" scoped>
.home-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.home-tabs {
  display: flex;
  background: #fff;
  padding: 20rpx 32rpx;
  gap: 16rpx;
}

.home-tab {
  padding: 12rpx 28rpx;
  border-radius: 32rpx;
  font-size: 26rpx;
  color: #666;
  background: #f5f5f5;
}

.home-tab.active {
  color: #fff;
  background: #4A90D9;
}

.home-list {
  flex: 1;
  padding-top: 8rpx;
}

.home-card {
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
  margin: 16rpx 32rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.06);
}

.home-card-image {
  width: 100%;
  height: 320rpx;
  background: #f0f0f0;
}

.home-card-info {
  padding: 20rpx 24rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.home-card-name {
  font-size: 34rpx;
  font-weight: 600;
  color: #333;
}

.home-card-level {
  font-size: 24rpx;
  color: #4A90D9;
  background: rgba(74, 144, 217, 0.1);
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
}

.home-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
  font-size: 28rpx;
  color: #999;
}

.home-empty-hint {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #bbb;
}
</style>
