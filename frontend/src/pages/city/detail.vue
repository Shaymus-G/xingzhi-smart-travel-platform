<script setup lang="ts">
/**
 * 城市详情页 — 展示城市信息 + 五类资源（景点/酒店/餐厅/娱乐/商场）
 */
import { ref, reactive } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import NavBar from '@/components/NavBar.vue'
import ScenicCard from '@/components/ScenicCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import Loading from '@/components/Loading.vue'
import SafeImage from '@/components/SafeImage.vue'
import { openResourceDetail } from '@/utils/navigation'
import {
  getCityDetail, getScenics, getHotels, getRestaurants,
  getEntertainments, getMalls,
} from '@/api/travel'
import type { City, ScenicSpot, Hotel, Restaurant, Entertainment, ShoppingMall } from '@/types/travel'

// ==================== 类型 ====================

type CityResourceTab = 'scenic_spot' | 'hotel' | 'restaurant' | 'entertainment' | 'shopping_mall'

interface TabState<T> {
  items: T[]
  loading: boolean
  loaded: boolean
  error: string | null
}

const TABS: Array<{ key: CityResourceTab; label: string }> = [
  { key: 'scenic_spot', label: '景点' },
  { key: 'hotel', label: '酒店' },
  { key: 'restaurant', label: '餐厅' },
  { key: 'entertainment', label: '娱乐' },
  { key: 'shopping_mall', label: '商场' },
]

// ==================== 路由参数 ====================

const cityId = ref(0)
const city = ref<City | null>(null)
const cityLoading = ref(false)
const cityError = ref<string | null>(null)
const currentTab = ref<CityResourceTab>('scenic_spot')

// ==================== 五类资源状态 ====================

const scenicState = reactive<TabState<ScenicSpot>>({ items: [], loading: false, loaded: false, error: null })
const hotelState = reactive<TabState<Hotel>>({ items: [], loading: false, loaded: false, error: null })
const restaurantState = reactive<TabState<Restaurant>>({ items: [], loading: false, loaded: false, error: null })
const entertainmentState = reactive<TabState<Entertainment>>({ items: [], loading: false, loaded: false, error: null })
const mallState = reactive<TabState<ShoppingMall>>({ items: [], loading: false, loaded: false, error: null })

function getState(tab: CityResourceTab): TabState<any> {
  switch (tab) {
    case 'scenic_spot': return scenicState
    case 'hotel': return hotelState
    case 'restaurant': return restaurantState
    case 'entertainment': return entertainmentState
    case 'shopping_mall': return mallState
  }
}

// ==================== 城市信息加载 ====================

async function loadCityInfo(): Promise<void> {
  if (!cityId.value) return
  cityLoading.value = true
  cityError.value = null
  try {
    city.value = await getCityDetail(cityId.value)
  } catch (err: unknown) {
    cityError.value = err instanceof Error ? err.message : '加载失败'
    uni.showToast({ title: cityError.value, icon: 'none' })
  } finally {
    cityLoading.value = false
  }
}

// ==================== 资源加载 ====================

async function loadScenics(): Promise<void> {
  const s = scenicState
  if (s.loaded || s.loading) return
  s.loading = true; s.error = null
  try { s.items = await getScenics({ city_id: cityId.value, limit: 50 }) || []; s.loaded = true }
  catch (err: unknown) { s.error = (err instanceof Error ? err.message : '景点加载失败'); s.loaded = false }
  finally { s.loading = false }
}

async function loadHotels(): Promise<void> {
  const s = hotelState
  if (s.loaded || s.loading) return
  s.loading = true; s.error = null
  try { s.items = await getHotels({ city_id: cityId.value, limit: 50 }) || []; s.loaded = true }
  catch (err: unknown) { s.error = (err instanceof Error ? err.message : '酒店加载失败'); s.loaded = false }
  finally { s.loading = false }
}

async function loadRestaurants(): Promise<void> {
  const s = restaurantState
  if (s.loaded || s.loading) return
  s.loading = true; s.error = null
  try { s.items = await getRestaurants({ city_id: cityId.value, limit: 50 }) || []; s.loaded = true }
  catch (err: unknown) { s.error = (err instanceof Error ? err.message : '餐厅加载失败'); s.loaded = false }
  finally { s.loading = false }
}

async function loadEntertainments(): Promise<void> {
  const s = entertainmentState
  if (s.loaded || s.loading) return
  s.loading = true; s.error = null
  try { s.items = await getEntertainments({ city_id: cityId.value, limit: 50 }) || []; s.loaded = true }
  catch (err: unknown) { s.error = (err instanceof Error ? err.message : '娱乐资源加载失败'); s.loaded = false }
  finally { s.loading = false }
}

async function loadMalls(): Promise<void> {
  const s = mallState
  if (s.loaded || s.loading) return
  s.loading = true; s.error = null
  try { s.items = await getMalls({ city_id: cityId.value, limit: 50 }) || []; s.loaded = true }
  catch (err: unknown) { s.error = (err instanceof Error ? err.message : '商场数据加载失败'); s.loaded = false }
  finally { s.loading = false }
}

async function ensureTabLoaded(tab: CityResourceTab): Promise<void> {
  switch (tab) {
    case 'scenic_spot': await loadScenics(); return
    case 'hotel': await loadHotels(); return
    case 'restaurant': await loadRestaurants(); return
    case 'entertainment': await loadEntertainments(); return
    case 'shopping_mall': await loadMalls(); return
  }
}

// ==================== Tab 切换 ====================

function onTabChange(tab: CityResourceTab): void {
  currentTab.value = tab
  void ensureTabLoaded(tab)
}

// ==================== 导航 ====================

function goScenicDetail(id: number): void {
  uni.navigateTo({ url: `/pages/scenic/detail?id=${id}` })
}

function onResourceTap(type: CityResourceTab, id: number): void {
  openResourceDetail(type, id)
}

// ==================== 生命周期 ====================

onLoad((options: any) => {
  const id = Number(options?.id)
  if (!id || isNaN(id)) {
    uni.showToast({ title: '城市ID无效', icon: 'none' })
    uni.navigateBack()
    return
  }
  cityId.value = id
  // 并行加载城市信息 + 默认 Tab (景点)
  void Promise.all([loadCityInfo(), ensureTabLoaded('scenic_spot')])
})
</script>

<template>
  <view class="city-detail-page">
    <NavBar :title="city?.name || '城市详情'" :show-back="true" />

    <scroll-view class="city-scroll" scroll-y enhanced :show-scrollbar="false">
      <Loading :visible="cityLoading" />

      <template v-if="!cityLoading && city">
        <!-- 城市头部 -->
        <view class="city-header">
          <SafeImage class="city-cover" :src="city.cover_image" mode="aspectFill" />
          <view class="city-header-info">
            <view class="city-name-row">
              <text class="city-name">{{ city.name }}</text>
              <text v-if="city.level" class="city-level-tag">{{ city.level }}</text>
            </view>
            <text v-if="city.province" class="city-province">{{ city.province }}</text>
            <text v-if="city.description" class="city-desc">{{ city.description }}</text>
          </view>
        </view>

        <!-- Tab 横向滚动 -->
        <scroll-view class="city-tabs-scroll" scroll-x :show-scrollbar="false">
          <view class="city-tabs">
            <view
              v-for="tab in TABS"
              :key="tab.key"
              class="city-tab"
              :class="{ active: currentTab === tab.key }"
              @tap="onTabChange(tab.key)"
            >
              {{ tab.label }}
            </view>
          </view>
        </scroll-view>

        <!-- 通用资源 Tab 内容 -->
        <view v-for="tab in TABS" :key="tab.key">
          <view v-if="currentTab === tab.key" class="city-section">
            <!-- Loading -->
            <view v-if="getState(tab.key).loading" class="city-sub-status">
              <text>加载中...</text>
            </view>

            <!-- Error -->
            <view v-else-if="getState(tab.key).error" class="city-sub-status city-sub-error">
              <text>{{ getState(tab.key).error }}</text>
              <view class="city-retry-btn" @tap="ensureTabLoaded(tab.key)">
                <text>重试</text>
              </view>
            </view>

            <!-- Empty -->
            <EmptyState
              v-else-if="getState(tab.key).loaded && getState(tab.key).items.length === 0"
              :text="'该城市暂无' + tab.label + (tab.key === 'entertainment' ? '资源' : tab.key === 'shopping_mall' ? '数据' : '')"
            />

            <!-- Ready — scenic_spot uses ScenicCard -->
            <template v-else-if="getState(tab.key).loaded && tab.key === 'scenic_spot'">
              <view v-for="s in scenicState.items" :key="s.id" class="city-card-wrapper">
                <ScenicCard
                  :scenic-id="s.id" :name="s.name" :image-url="s.image_url"
                  :score="s.score" :price="s.price" :category="s.category" :address="s.address"
                  @click="goScenicDetail"
                />
              </view>
            </template>

            <!-- Ready — other types use simple card -->
            <template v-else-if="getState(tab.key).loaded">
              <view
                v-for="item in getState(tab.key).items"
                :key="item.id"
                class="city-simple-card"
                @tap="onResourceTap(tab.key, item.id)"
              >
                <SafeImage class="city-simple-card-img" :src="item.image_url" mode="aspectFill" />
                <view class="city-simple-card-body">
                  <text class="city-simple-card-name">{{ item.name }}</text>
                  <text class="city-simple-card-meta">
                    <text v-if="item.category">{{ item.category }}  </text>
                    <text v-if="item.score">★ {{ item.score }}  </text>
                    <text v-if="tab.key === 'restaurant' && item.price_level">{{ item.price_level }}</text>
                    <text v-else-if="item.price != null">¥{{ item.price }}</text>
                  </text>
                  <text v-if="item.address" class="city-simple-card-addr">{{ item.address }}</text>
                </view>
              </view>
            </template>
          </view>
        </view>
      </template>

      <!-- 城市加载失败 -->
      <view v-else-if="!cityLoading && cityError" class="city-sub-status city-sub-error" style="padding-top:200rpx;">
        <text>{{ cityError }}</text>
      </view>

      <view style="height: 40rpx;" />
    </scroll-view>
  </view>
</template>

<style lang="scss" scoped>
.city-detail-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.city-scroll {
  flex: 1;
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

.city-name-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.city-name {
  font-size: 38rpx;
  font-weight: 700;
  color: #333;
}

.city-level-tag {
  font-size: 24rpx;
  color: #4A90D9;
  background: rgba(74, 144, 217, 0.1);
  padding: 4rpx 14rpx;
  border-radius: 8rpx;
}

.city-province {
  font-size: 26rpx;
  color: #666;
  display: block;
  margin-top: 8rpx;
}

.city-desc {
  font-size: 26rpx;
  color: #999;
  display: block;
  margin-top: 8rpx;
  line-height: 1.6;
}

// Tabs
.city-tabs-scroll {
  white-space: nowrap;
  background: #fff;
  margin-top: 16rpx;
}

.city-tabs {
  display: inline-flex;
  padding: 0 24rpx;
}

.city-tab {
  display: inline-block;
  padding: 24rpx 24rpx;
  font-size: 28rpx;
  color: #666;
  border-bottom: 4rpx solid transparent;
  white-space: nowrap;
}

.city-tab.active {
  color: #4A90D9;
  font-weight: 600;
  border-bottom-color: #4A90D9;
}

// Section
.city-section {
  background: #fff;
  padding: 16rpx 32rpx;
  min-height: 200rpx;
}

.city-sub-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 80rpx;
  font-size: 28rpx;
  color: #999;
}

.city-sub-error {
  color: #d93025;
}

.city-retry-btn {
  margin-top: 16rpx;
  padding: 10rpx 36rpx;
  border: 1px solid #4A90D9;
  border-radius: 24rpx;
  font-size: 26rpx;
  color: #4A90D9;
}

.city-card-wrapper {
  margin-bottom: 8rpx;
}

.city-simple-card {
  display: flex;
  background: #fafafa;
  border-radius: 12rpx;
  overflow: hidden;
  margin: 12rpx 0;
}

.city-simple-card-img {
  width: 180rpx;
  height: 140rpx;
  flex-shrink: 0;
  background: #e0e0e0;
}

.city-simple-card-body {
  flex: 1;
  padding: 16rpx 20rpx;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.city-simple-card-name {
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
}

.city-simple-card-meta {
  font-size: 24rpx;
  color: #666;
  margin-top: 6rpx;
}

.city-simple-card-addr {
  font-size: 22rpx;
  color: #999;
  margin-top: 4rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
