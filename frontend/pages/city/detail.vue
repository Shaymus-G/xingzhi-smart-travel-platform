<script setup lang="ts">
/**
 * 城市详情页 — 展示城市信息 + 景点/酒店/餐厅
 */
import { ref, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'
import ScenicCard from '@/components/ScenicCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import Loading from '@/components/Loading.vue'
import { getCityDetail, getScenics, getHotels, getRestaurants } from '@/api/travel'
import type { City, ScenicSpot, Hotel, Restaurant } from '@/types/travel'

// ========== 路由参数 ==========
const cityId = ref(0)

// ========== 数据 ==========
const city = ref<City | null>(null)
const scenics = ref<ScenicSpot[]>([])
const hotels = ref<Hotel[]>([])
const restaurants = ref<Restaurant[]>([])
const loading = ref(false)
const currentTab = ref<'scenics' | 'hotels' | 'restaurants'>('scenics')

// ========== 图片兜底 ==========
const FALLBACK = '/static/logo.png'

// ========== 方法 ==========

async function loadAll() {
  if (!cityId.value) return
  loading.value = true
  try {
    const [cityData, scenicData, hotelData, restData] = await Promise.all([
      getCityDetail(cityId.value),
      getScenics({ city_id: cityId.value, limit: 20 }),
      getHotels({ city_id: cityId.value, limit: 10 }),
      getRestaurants({ city_id: cityId.value, limit: 10 }),
    ])
    city.value = cityData
    scenics.value = scenicData || []
    hotels.value = hotelData || []
    restaurants.value = restData || []
  } catch (err) {
    const msg = err instanceof Error ? err.message : '加载失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    loading.value = false
  }
}

function goScenicDetail(id: number) {
  uni.navigateTo({ url: `/pages/scenic/detail?id=${id}` })
}

function onHotelTap(_id: number) {
  uni.showToast({ title: '酒店详情页开发中', icon: 'none' })
}

function onRestaurantTap(_id: number) {
  uni.showToast({ title: '餐厅详情页开发中', icon: 'none' })
}

// ========== 生命周期 ==========
onMounted(() => {
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as Record<string, unknown>
  const options = (currentPage?.options || {}) as Record<string, string>
  const id = Number(options?.id)
  if (!id || isNaN(id)) {
    uni.showToast({ title: '城市ID无效', icon: 'none' })
    uni.navigateBack()
    return
  }
  cityId.value = id
  loadAll()
})
</script>

<template>
  <view class="city-detail-page">
    <NavBar :title="city?.name || '城市详情'" :show-back="true" />

    <scroll-view class="city-scroll" scroll-y enhanced :show-scrollbar="false">
      <Loading :visible="loading" />

      <template v-if="!loading && city">
        <!-- 城市头部 -->
        <view class="city-header">
          <image
            class="city-cover"
            :src="city.cover_image || FALLBACK"
            mode="aspectFill"
          />
          <view class="city-header-info">
            <view class="city-name-row">
              <text class="city-name">{{ city.name }}</text>
              <text v-if="city.level" class="city-level-tag">{{ city.level }}</text>
            </view>
            <text v-if="city.province" class="city-province">{{ city.province }}</text>
            <text v-if="city.description" class="city-desc">{{ city.description }}</text>
          </view>
        </view>

        <!-- Tab 切换 -->
        <view class="city-tabs">
          <view
            v-for="tab in [
              { key: 'scenics', label: '景点', count: scenics.length },
              { key: 'hotels', label: '酒店', count: hotels.length },
              { key: 'restaurants', label: '餐厅', count: restaurants.length },
            ]"
            :key="tab.key"
            class="city-tab"
            :class="{ active: currentTab === tab.key }"
            @tap="currentTab = tab.key as 'scenics' | 'hotels' | 'restaurants'"
          >
            {{ tab.label }} ({{ tab.count }})
          </view>
        </view>

        <!-- 景点 -->
        <view v-if="currentTab === 'scenics'" class="city-section">
          <EmptyState v-if="scenics.length === 0" text="暂无景点" />
          <view v-for="s in scenics" :key="s.id" class="city-card-wrapper">
            <ScenicCard
              :scenic-id="s.id"
              :name="s.name"
              :image-url="s.image_url"
              :score="s.score"
              :price="s.price"
              :category="s.category"
              :address="s.address"
              @click="goScenicDetail"
            />
          </view>
        </view>

        <!-- 酒店 -->
        <view v-if="currentTab === 'hotels'" class="city-section">
          <EmptyState v-if="hotels.length === 0" text="暂无酒店" />
          <view
            v-for="h in hotels"
            :key="h.id"
            class="city-simple-card"
            @tap="onHotelTap(h.id)"
          >
            <image
              class="city-simple-card-img"
              :src="h.image_url || FALLBACK"
              mode="aspectFill"
            />
            <view class="city-simple-card-body">
              <text class="city-simple-card-name">{{ h.name }}</text>
              <text class="city-simple-card-meta">
                <text v-if="h.score">★ {{ h.score }}  </text>
                <text v-if="h.price">¥{{ h.price }}</text>
              </text>
              <text v-if="h.address" class="city-simple-card-addr">{{ h.address }}</text>
            </view>
          </view>
        </view>

        <!-- 餐厅 -->
        <view v-if="currentTab === 'restaurants'" class="city-section">
          <EmptyState v-if="restaurants.length === 0" text="暂无餐厅" />
          <view
            v-for="r in restaurants"
            :key="r.id"
            class="city-simple-card"
            @tap="onRestaurantTap(r.id)"
          >
            <image
              class="city-simple-card-img"
              :src="r.image_url || FALLBACK"
              mode="aspectFill"
            />
            <view class="city-simple-card-body">
              <text class="city-simple-card-name">{{ r.name }}</text>
              <text class="city-simple-card-meta">
                <text v-if="r.category">{{ r.category }}  </text>
                <text v-if="r.score">★ {{ r.score }}  </text>
                <text v-if="r.price_level">{{ r.price_level }}</text>
              </text>
              <text v-if="r.address" class="city-simple-card-addr">{{ r.address }}</text>
            </view>
          </view>
        </view>
      </template>

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

.city-tabs {
  display: flex;
  background: #fff;
  margin-top: 16rpx;
  padding: 0 32rpx;
}

.city-tab {
  flex: 1;
  text-align: center;
  padding: 24rpx 0;
  font-size: 28rpx;
  color: #666;
  border-bottom: 4rpx solid transparent;
}

.city-tab.active {
  color: #4A90D9;
  font-weight: 600;
  border-bottom-color: #4A90D9;
}

.city-section {
  background: #fff;
  padding: 16rpx 32rpx;
  min-height: 200rpx;
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
