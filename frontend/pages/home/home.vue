<script setup lang="ts">
/**
 * 首页 — 城市与旅游资源浏览入口
 * 加载热门城市 + 热门景点，支持城市等级筛选
 */
import { ref, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'
import CityCard from '@/components/CityCard.vue'
import ScenicCard from '@/components/ScenicCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import Loading from '@/components/Loading.vue'
import { getCities, getScenics } from '@/api/travel'
import type { City, ScenicSpot } from '@/types/travel'

// ========== 数据状态 ==========
const cities = ref<City[]>([])
const scenics = ref<ScenicSpot[]>([])
const loading = ref(false)
const errorMsg = ref('')
const selectedLevel = ref('热门')

// ========== 方法 ==========

async function loadCities() {
  try {
    const data = await getCities({
      level: selectedLevel.value,
      limit: 10,
    })
    cities.value = data || []
  } catch (err) {
    console.error('[Home] loadCities error:', err)
  }
}

async function loadScenics() {
  try {
    const data = await getScenics({ limit: 10 })
    scenics.value = data || []
  } catch (err) {
    console.error('[Home] loadScenics error:', err)
  }
}

async function loadAll() {
  loading.value = true
  errorMsg.value = ''
  try {
    await Promise.all([loadCities(), loadScenics()])
  } catch (err) {
    const msg = err instanceof Error ? err.message : '加载失败'
    errorMsg.value = msg
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    loading.value = false
  }
}

function onLevelChange(level: string) {
  selectedLevel.value = level
  loadCities()
}

function goCityDetail(id: number) {
  uni.navigateTo({ url: `/pages/city/detail?id=${id}` })
}

function goScenicDetail(id: number) {
  uni.navigateTo({ url: `/pages/scenic/detail?id=${id}` })
}

function goAiChat() {
  uni.switchTab({ url: '/pages/ai/chat' })
}

// ========== 生命周期 ==========
onMounted(() => {
  loadAll()
})
</script>

<template>
  <view class="home-page">
    <NavBar title="行知 · 发现城市" />

    <scroll-view class="home-scroll" scroll-y enhanced :show-scrollbar="false">
      <!-- 城市等级筛选 -->
      <view class="home-tabs">
        <view
          v-for="tab in ['热门', '普通', '小众']"
          :key="tab"
          class="home-tab"
          :class="{ active: tab === selectedLevel }"
          @tap="onLevelChange(tab)"
        >
          {{ tab }}
        </view>
      </view>

      <Loading :visible="loading" />

      <!-- 错误状态 -->
      <EmptyState
        v-if="errorMsg && !loading"
        :text="errorMsg"
        sub-text="请确认后端服务已启动"
      />

      <!-- 热门城市 -->
      <view v-if="!loading && !errorMsg" class="home-section">
        <view class="home-section-header">
          <text class="home-section-title">{{ selectedLevel }}城市</text>
        </view>
        <EmptyState
          v-if="cities.length === 0"
          text="暂无城市数据"
          sub-text="请确认数据库中已导入城市数据"
        />
        <CityCard
          v-for="city in cities"
          :key="city.id"
          :city-id="city.id"
          :name="city.name"
          :province="city.province"
          :cover-image="city.cover_image"
          :level="city.level"
          :description="city.description"
          @click="goCityDetail"
        />
      </view>

      <!-- 热门景点 -->
      <view v-if="!loading && !errorMsg" class="home-section">
        <view class="home-section-header">
          <text class="home-section-title">热门景点</text>
        </view>
        <EmptyState
          v-if="scenics.length === 0"
          text="暂无景点数据"
          sub-text="请确认数据库中已导入景点数据"
        />
        <view v-for="scenic in scenics" :key="scenic.id" class="home-scenic-wrapper">
          <ScenicCard
            :scenic-id="scenic.id"
            :name="scenic.name"
            :image-url="scenic.image_url"
            :score="scenic.score"
            :price="scenic.price"
            :category="scenic.category"
            :address="scenic.address"
            @click="goScenicDetail"
          />
        </view>
      </view>

      <!-- AI 助手入口 -->
      <view v-if="!loading && !errorMsg" class="home-ai-entry" @tap="goAiChat">
        <text class="home-ai-icon">🤖</text>
        <view class="home-ai-info">
          <text class="home-ai-title">AI 旅行助手</text>
          <text class="home-ai-sub">智能规划你的旅行</text>
        </view>
        <text class="home-ai-arrow">›</text>
      </view>

      <!-- 底部安全距离 -->
      <view style="height: 40rpx;" />
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

.home-scroll {
  flex: 1;
}

.home-tabs {
  display: flex;
  background: #fff;
  padding: 20rpx 32rpx;
  gap: 16rpx;
  position: sticky;
  top: 0;
  z-index: 10;
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

.home-section {
  margin-top: 8rpx;
}

.home-section-header {
  padding: 24rpx 32rpx 8rpx;
}

.home-section-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #333;
}

.home-scenic-wrapper {
  padding: 0 32rpx;
}

.home-ai-entry {
  display: flex;
  align-items: center;
  margin: 24rpx 32rpx;
  padding: 28rpx 24rpx;
  background: linear-gradient(135deg, #4A90D9, #6BA5E7);
  border-radius: 16rpx;
}

.home-ai-icon {
  font-size: 52rpx;
  margin-right: 20rpx;
}

.home-ai-info {
  flex: 1;
}

.home-ai-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #fff;
  display: block;
}

.home-ai-sub {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
  margin-top: 4rpx;
}

.home-ai-arrow {
  font-size: 40rpx;
  color: rgba(255, 255, 255, 0.8);
}
</style>
