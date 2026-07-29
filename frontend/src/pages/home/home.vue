<script setup lang="ts">
/**
 * 首页 — 城市与旅游资源浏览入口
 * 加载热门城市 + 热门景点，支持城市等级筛选
 */
import { ref, reactive, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import NavBar from '@/components/NavBar.vue'
import CityCard from '@/components/CityCard.vue'
import ScenicCard from '@/components/ScenicCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import Loading from '@/components/Loading.vue'
import RecommendationSection from '@/components/RecommendationSection.vue'
import { getCities, getScenics } from '@/api/travel'
import { getCollaborativeCities } from '@/api/recommend'
import { normalizeRecommendCity } from '@/utils/recommend'
import { useUserStore } from '@/stores/user'
import type { City, ScenicSpot } from '@/types/travel'
import type { CollaborativeRecommendCity, NormalizedRecommendCity } from '@/types/recommend'

// ========== 数据状态 ==========
const cities = ref<City[]>([])
const scenics = ref<ScenicSpot[]>([])
const loading = ref(false)
const errorMsg = ref('')
const selectedLevel = ref('热门')

const CITY_CANDIDATE_LIMIT = 50
const CITY_DISPLAY_LIMIT = 10
let citiesRequestVersion = 0

// ========== 用户状态 ==========

const userStore = useUserStore()

// ========== Collaborative 推荐状态 ==========

const COLLABORATIVE_LIMIT = 8

interface CollaborativeState {
  cities: NormalizedRecommendCity[]
  loading: boolean
  error: string | null
  loaded: boolean
}

const collaborativeState = reactive<CollaborativeState>({
  cities: [],
  loading: false,
  error: null,
  loaded: false,
})

// ========== 方法 ==========

/** 标准化省份分组键：trim + 空值统一 */
function normalizeProvinceKey(
  province: string | null | undefined,
): string {
  const value = province?.trim()
  return value || '__UNKNOWN_PROVINCE__'
}

/** 城市多样化：去重 → 按省份分组 → Round-Robin → 取 displayLimit 条 */
function diversifyCities(
  candidates: City[],
  displayLimit: number,
): City[] {
  const source = Array.isArray(candidates) ? candidates : []
  const seenCityIds = new Set<number>()
  const validCities: City[] = []

  for (const city of source) {
    if (!city || typeof city !== 'object') continue
    if (
      !Number.isFinite(city.id) ||
      !Number.isInteger(city.id) ||
      city.id <= 0 ||
      seenCityIds.has(city.id)
    ) {
      continue
    }
    seenCityIds.add(city.id)
    validCities.push(city)
  }

  const provinceGroups = new Map<string, City[]>()
  const provinceOrder: string[] = []

  for (const city of validCities) {
    const key = normalizeProvinceKey(city.province)
    let group = provinceGroups.get(key)
    if (!group) {
      group = []
      provinceGroups.set(key, group)
      provinceOrder.push(key)
    }
    group.push(city)
  }

  const result: City[] = []
  const groupIndexes = new Map<string, number>()
  for (const key of provinceOrder) {
    groupIndexes.set(key, 0)
  }

  while (result.length < displayLimit) {
    let addedInRound = false
    for (const key of provinceOrder) {
      const group = provinceGroups.get(key)
      const index = groupIndexes.get(key) ?? 0
      if (!group || index >= group.length) continue
      result.push(group[index])
      groupIndexes.set(key, index + 1)
      addedInRound = true
      if (result.length >= displayLimit) break
    }
    if (!addedInRound) break
  }

  return result
}

/** 加载城市列表（候选池 + 多样化 + 竞态保护） */
async function loadCities(): Promise<void> {
  const requestVersion = ++citiesRequestVersion
  const requestedLevel = selectedLevel.value

  try {
    const data = await getCities({
      level: requestedLevel,
      limit: CITY_CANDIDATE_LIMIT,
    })

    if (
      requestVersion !== citiesRequestVersion ||
      requestedLevel !== selectedLevel.value
    ) {
      return
    }

    cities.value = diversifyCities(
      Array.isArray(data) ? data : [],
      CITY_DISPLAY_LIMIT,
    )
  } catch (err) {
    if (
      requestVersion !== citiesRequestVersion ||
      requestedLevel !== selectedLevel.value
    ) {
      return
    }
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
  if (selectedLevel.value === level) return
  selectedLevel.value = level
  void loadCities()
}

let navigating = false

function resetNavigating() {
  setTimeout(() => {
    navigating = false
  }, 800)
}

function goCityDetail(id: number | string) {
  const cityId = Number(id)
  if (!Number.isFinite(cityId) || cityId <= 0) {
    uni.showToast({ title: '城市 ID 无效', icon: 'none' })
    return
  }

  if (navigating) {
    return
  }
  navigating = true

  const primaryUrl = `/pages/city/detail?id=${cityId}`
  const fallbackUrl = `pages/city/detail?id=${cityId}`

  uni.navigateTo({
    url: primaryUrl,
    success(_res) {
    },
    fail(err) {
      console.error('[home] navigate city/detail primary failed:', JSON.stringify(err))
      uni.navigateTo({
        url: fallbackUrl,
        success(res2) {
          console.log('[home] navigate city/detail fallback success:', JSON.stringify(res2))
        },
        fail(err2) {
          console.error('[home] navigate city/detail fallback failed:', JSON.stringify(err2))
          uni.showToast({ title: '页面跳转失败', icon: 'none' })
        },
        complete() {
          resetNavigating()
        },
      })
    },
    complete(res) {
      console.log('[home] navigate city/detail primary complete:', JSON.stringify(res))
      if (navigating) resetNavigating()
    },
  })
}

function goScenicDetail(id: number | string) {
  const scenicId = Number(id)
  if (!Number.isFinite(scenicId) || scenicId <= 0) {
    uni.showToast({ title: '景点 ID 无效', icon: 'none' })
    return
  }

  if (navigating) {
    return
  }
  navigating = true

  const primaryUrl = `/pages/scenic/detail?id=${scenicId}`
  const fallbackUrl = `pages/scenic/detail?id=${scenicId}`

  uni.navigateTo({
    url: primaryUrl,
    success(_res) {
    },
    fail(err) {
      console.error('[home] navigate scenic/detail primary failed:', JSON.stringify(err))
      uni.navigateTo({
        url: fallbackUrl,
        success(res2) {
          console.log('[home] navigate scenic/detail fallback success:', JSON.stringify(res2))
        },
        fail(err2) {
          console.error('[home] navigate scenic/detail fallback failed:', JSON.stringify(err2))
          uni.showToast({ title: '页面跳转失败', icon: 'none' })
        },
        complete() {
          resetNavigating()
        },
      })
    },
    complete(res) {
      console.log('[home] navigate scenic/detail primary complete:', JSON.stringify(res))
      if (navigating) resetNavigating()
    },
  })
}

function goAiChat() {
  uni.switchTab({ url: '/pages/ai/chat' })
}

// ========== Collaborative ==========

let collaborativeRequestVersion = 0

/** 标准化协同过滤推荐列表：标准化、过滤无效 ID、按 ID 去重、保序、限制数量 */
function normalizeCollaborativeCities(
  rawCities: CollaborativeRecommendCity[],
): NormalizedRecommendCity[] {
  const source = Array.isArray(rawCities) ? rawCities : []
  const seen = new Set<number>()
  const result: NormalizedRecommendCity[] = []

  for (const rawCity of source) {
    const city = normalizeRecommendCity(rawCity)

    if (
      !Number.isFinite(city.id) ||
      !Number.isInteger(city.id) ||
      city.id <= 0 ||
      seen.has(city.id)
    ) {
      continue
    }

    seen.add(city.id)
    result.push(city)

    if (result.length >= COLLABORATIVE_LIMIT) {
      break
    }
  }

  return result
}

/** 重置协同过滤状态（退出登录时调用，使旧请求失效） */
function resetCollaborativeState(): void {
  collaborativeRequestVersion += 1
  collaborativeState.cities = []
  collaborativeState.loading = false
  collaborativeState.error = null
  collaborativeState.loaded = false
}

/** 加载协同过滤推荐 */
async function loadCollaborative(): Promise<void> {
  if (!userStore.isLoggedIn) {
    resetCollaborativeState()
    return
  }

  if (collaborativeState.loading || collaborativeState.loaded) {
    return
  }

  const requestVersion = ++collaborativeRequestVersion

  collaborativeState.loading = true
  collaborativeState.error = null

  try {
    const rawCities = await getCollaborativeCities(COLLABORATIVE_LIMIT)

    if (requestVersion !== collaborativeRequestVersion) {
      return
    }

    collaborativeState.cities = normalizeCollaborativeCities(rawCities)
    collaborativeState.loaded = true
  } catch (error: unknown) {
    if (requestVersion !== collaborativeRequestVersion) {
      return
    }

    collaborativeState.cities = []
    const message = error instanceof Error ? error.message.trim() : ''
    collaborativeState.error = message || '个性化推荐加载失败'
    collaborativeState.loaded = false
  } finally {
    if (requestVersion === collaborativeRequestVersion) {
      collaborativeState.loading = false
    }
  }
}

// ========== 生命周期 ==========

onMounted(() => {
  loadAll()
})

onShow(() => {
  if (!userStore.isLoggedIn) {
    resetCollaborativeState()
    return
  }
  void loadCollaborative()
})
</script>

<template>
  <view class="home-page">
    <NavBar title="行知 · 发现城市" />

    <scroll-view class="home-scroll" scroll-y enhanced :show-scrollbar="false">
      <!-- 猜你喜欢 -->
      <RecommendationSection
        v-if="
          userStore.isLoggedIn &&
          collaborativeState.cities.length > 0
        "
        title="猜你喜欢"
        :cities="collaborativeState.cities"
        variant="collaborative"
        @click="goCityDetail"
      />

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
