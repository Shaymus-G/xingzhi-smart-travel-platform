<script setup lang="ts">
/**
 * 通用资源详情页 — 酒店 / 餐厅 / 娱乐 / 商场
 */
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import NavBar from '@/components/NavBar.vue'
import SafeImage from '@/components/SafeImage.vue'
import ResourceSocialSection from '@/components/ResourceSocialSection.vue'
import { getHotelDetail, getRestaurantDetail, getEntertainmentDetail, getMallDetail } from '@/api/travel'
import type { Hotel, Restaurant, Entertainment, ShoppingMall } from '@/types/travel'

// ==================== 类型 ====================

type SupportedDetailType = 'hotel' | 'restaurant' | 'entertainment' | 'shopping_mall'

const SUPPORTED_TYPES: ReadonlySet<string> = new Set<SupportedDetailType>([
  'hotel', 'restaurant', 'entertainment', 'shopping_mall',
])

type DetailError = 'invalidType' | 'invalidId' | 'notFound' | 'network' | 'unknown'

type ResourceDetailEntity =
  | { type: 'hotel'; data: Hotel }
  | { type: 'restaurant'; data: Restaurant }
  | { type: 'entertainment'; data: Entertainment }
  | { type: 'shopping_mall'; data: ShoppingMall }

interface DetailViewModel {
  name: string
  imageUrl: string | null
  description: string | null
  address: string | null
  score: number | null
  priceText: string | null
  priceLabel: string | null
  categoryText: string | null
  openTime: string | null
}

// ==================== API 加载映射 ====================

const DETAIL_LOADERS: Record<SupportedDetailType, (id: number) => Promise<ResourceDetailEntity>> = {
  hotel: async (id: number) => ({ type: 'hotel', data: await getHotelDetail(id) }),
  restaurant: async (id: number) => ({ type: 'restaurant', data: await getRestaurantDetail(id) }),
  entertainment: async (id: number) => ({ type: 'entertainment', data: await getEntertainmentDetail(id) }),
  shopping_mall: async (id: number) => ({ type: 'shopping_mall', data: await getMallDetail(id) }),
}

// ==================== 状态 ====================

const resourceType = ref<SupportedDetailType | null>(null)
const resourceId = ref<number | null>(null)
const isLoading = ref(false)
const loadError = ref<DetailError | null>(null)
const resource = ref<ResourceDetailEntity | null>(null)
let _loading = false

// ==================== 生命周期 ====================

onLoad((rawOptions: Record<string, string> | undefined) => {
  const typeVal = rawOptions?.type
  const idVal = rawOptions?.id

  // 校验 type
  if (!typeVal || !SUPPORTED_TYPES.has(typeVal)) {
    loadError.value = 'invalidType'
    return
  }
  resourceType.value = typeVal as SupportedDetailType

  // 校验 id（不使用 Number(x) || 0）
  const idNum = Number(idVal)
  if (!Number.isFinite(idNum) || !Number.isInteger(idNum) || idNum <= 0) {
    loadError.value = 'invalidId'
    return
  }
  resourceId.value = idNum

  // 动态标题
  const TITLE_MAP: Record<string, string> = {
    hotel: '酒店详情', restaurant: '餐厅详情',
    entertainment: '娱乐详情', shopping_mall: '商场详情',
  }
  uni.setNavigationBarTitle({ title: TITLE_MAP[typeVal] || '资源详情' })

  void loadResource()
})

// ==================== 数据加载 ====================

async function loadResource(): Promise<void> {
  if (_loading) return
  if (!resourceType.value || !resourceId.value) return

  const loader = DETAIL_LOADERS[resourceType.value]
  if (!loader) {
    loadError.value = 'invalidType'
    return
  }

  _loading = true
  isLoading.value = true
  loadError.value = null
  resource.value = null

  try {
    resource.value = await loader(resourceId.value)
  } catch (err: unknown) {
    loadError.value = classifyError(err)
  } finally {
    isLoading.value = false
    _loading = false
  }
}

// ==================== 错误分类 ====================

function classifyError(err: unknown): DetailError {
  const msg = err instanceof Error ? err.message : String(err ?? '')
  if (msg.includes('不存在') || msg.includes('not found') || msg.includes('404')) return 'notFound'
  if (msg.includes('网络') || msg.includes('超时') || msg.includes('timeout') || msg.includes('fail') || msg.includes('abort')) return 'network'
  return 'unknown'
}

const NAV_TITLES: Record<string, string> = {
  hotel: '酒店详情', restaurant: '餐厅详情',
  entertainment: '娱乐详情', shopping_mall: '商场详情',
}

// ==================== 导航 ====================

function goBack(): void {
  const pages = getCurrentPages()
  if (pages.length > 1) {
    uni.navigateBack()
  } else {
    uni.reLaunch({ url: '/pages/home/home' })
  }
}

// ==================== ViewModel ====================

const viewModel = computed<DetailViewModel | null>(() => {
  if (!resource.value) return null
  const e = resource.value

  if (e.type === 'hotel') {
    const h = e.data
    return {
      name: h.name,
      imageUrl: h.image_url ?? null,
      description: h.description ?? null,
      address: h.address ?? null,
      score: toFiniteNumber(h.score),
      priceText: toFiniteNumber(h.price) !== null ? `¥${toFiniteNumber(h.price)}` : null,
      priceLabel: null,
      categoryText: null,
      openTime: h.open_time ?? null,
    }
  }

  if (e.type === 'restaurant') {
    const r = e.data
    return {
      name: r.name,
      imageUrl: r.image_url ?? null,
      description: r.description ?? null,
      address: r.address ?? null,
      score: toFiniteNumber(r.score),
      priceText: r.price_level ?? null,
      priceLabel: null,
      categoryText: r.category ?? null,
      openTime: null,
    }
  }

  if (e.type === 'entertainment') {
    const en = e.data
    const price = toFiniteNumber(en.price)
    return {
      name: en.name,
      imageUrl: en.image_url ?? null,
      description: en.description ?? null,
      address: en.address ?? null,
      score: toFiniteNumber(en.score),
      priceText: price !== null ? `¥${price}` : null,
      priceLabel: price !== null ? '参考价格' : null,
      categoryText: en.category ?? null,
      openTime: en.open_time ?? null,
    }
  }

  // shopping_mall
  const m = e.data
  const mallPrice = toFiniteNumber(m.price)
  return {
    name: m.name,
    imageUrl: m.image_url ?? null,
    description: m.description ?? null,
    address: m.address ?? null,
    score: toFiniteNumber(m.score),
    priceText: mallPrice !== null ? `¥${mallPrice}` : null,
    priceLabel: mallPrice !== null ? '参考消费' : null,
    categoryText: m.category ?? null,
    openTime: m.open_time ?? null,
  }
})

// ==================== 格式化 ====================

function toFiniteNumber(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined) return null
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'string' && value.trim() !== '') {
    const n = Number(value)
    return Number.isFinite(n) ? n : null
  }
  return null
}

function fmtScore(score: number | null): string {
  if (score === null) return ''
  return `${score.toFixed(1)} 分`
}
</script>

<template>
  <view class="resource-detail-page">
    <NavBar
      :title="resourceType ? (NAV_TITLES[resourceType] || '资源详情') : '资源详情'"
      :show-back="true"
      @back="goBack"
    />

    <!-- 加载中 -->
    <view v-if="isLoading" class="rd-loading">
      <text>加载中...</text>
    </view>

    <!-- 错误：非法类型 -->
    <view v-else-if="loadError === 'invalidType'" class="rd-error">
      <text class="rd-error-title">不支持的资源类型</text>
      <view class="rd-action" @tap="goBack"><text>返回</text></view>
    </view>

    <!-- 错误：非法 ID -->
    <view v-else-if="loadError === 'invalidId'" class="rd-error">
      <text class="rd-error-title">资源参数无效</text>
      <view class="rd-action" @tap="goBack"><text>返回</text></view>
    </view>

    <!-- 错误：不存在 -->
    <view v-else-if="loadError === 'notFound'" class="rd-error">
      <text class="rd-error-title">资源不存在或已下线</text>
      <view class="rd-action" @tap="goBack"><text>返回</text></view>
    </view>

    <!-- 错误：网络 -->
    <view v-else-if="loadError === 'network'" class="rd-error">
      <text class="rd-error-title">网络请求失败，请检查网络后重试</text>
      <view class="rd-actions">
        <view class="rd-action" @tap="loadResource()"><text>重新加载</text></view>
        <view class="rd-action secondary" @tap="goBack"><text>返回</text></view>
      </view>
    </view>

    <!-- 错误：未知 -->
    <view v-else-if="loadError === 'unknown'" class="rd-error">
      <text class="rd-error-title">资源加载失败</text>
      <view class="rd-actions">
        <view class="rd-action" @tap="loadResource()"><text>重新加载</text></view>
        <view class="rd-action secondary" @tap="goBack"><text>返回</text></view>
      </view>
    </view>

    <!-- 详情内容 -->
    <scroll-view v-else-if="viewModel" class="rd-scroll" scroll-y>
      <!-- 主图 -->
      <view class="rd-image-wrap">
        <SafeImage
          :src="viewModel.imageUrl"
          mode="aspectFill"
          class="rd-image"
        />
      </view>

      <!-- 信息卡片 -->
      <view class="rd-card">
        <text class="rd-name">{{ viewModel.name }}</text>

        <view class="rd-meta" v-if="viewModel.score !== null || viewModel.priceText">
          <text v-if="viewModel.score !== null" class="rd-score">⭐ {{ fmtScore(viewModel.score) }}</text>
          <text v-if="viewModel.priceText" class="rd-price">{{ viewModel.priceText }}</text>
        </view>

        <view class="rd-tags" v-if="viewModel.categoryText">
          <text class="rd-tag">{{ viewModel.categoryText }}</text>
        </view>

        <view class="rd-field" v-if="viewModel.address">
          <text class="rd-field-label">📍 地址</text>
          <text class="rd-field-value">{{ viewModel.address }}</text>
        </view>

        <view class="rd-field" v-if="viewModel.openTime">
          <text class="rd-field-label">🕐 营业时间</text>
          <text class="rd-field-value">{{ viewModel.openTime }}</text>
        </view>

        <view class="rd-field" v-if="viewModel.description">
          <text class="rd-field-label">简介</text>
          <text class="rd-field-value">{{ viewModel.description }}</text>
        </view>
      </view>

      <!-- 收藏评论 -->
      <ResourceSocialSection
        v-if="resourceType && resourceId && resource"
        :target-type="resourceType"
        :target-id="resourceId"
        horizontal-padding="24rpx"
      />
    </scroll-view>
  </view>
</template>

<style lang="scss" scoped>
.resource-detail-page {
  min-height: 100vh;
  background: #f5f5f5;
}

// Loading / Error
.rd-loading, .rd-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
  font-size: 28rpx;
  color: #999;
}

.rd-error-title {
  font-size: 30rpx;
  color: #666;
  margin-bottom: 32rpx;
}

.rd-actions {
  display: flex;
  gap: 24rpx;
}

.rd-action {
  padding: 14rpx 40rpx;
  border: 1px solid #4A90D9;
  border-radius: 32rpx;
  font-size: 28rpx;
  color: #4A90D9;
}

.rd-action.secondary {
  border-color: #ccc;
  color: #999;
}

// Scroll
.rd-scroll {
  padding: 0 0 60rpx;
}

// Image
.rd-image-wrap {
  width: 100%;
  height: 420rpx;
  overflow: hidden;
  background: #e8e8e8;
}

.rd-image {
  width: 100%;
  height: 100%;
}

// Card
.rd-card {
  background: #fff;
  margin: -32rpx 24rpx 0;
  border-radius: 20rpx;
  padding: 32rpx 24rpx;
  position: relative;
  z-index: 1;
}

.rd-name {
  font-size: 36rpx;
  font-weight: 700;
  color: #333;
  display: block;
  margin-bottom: 16rpx;
}

.rd-meta {
  display: flex;
  align-items: center;
  gap: 24rpx;
  margin-bottom: 16rpx;
}

.rd-score {
  font-size: 28rpx;
  color: #FAAD14;
  font-weight: 600;
}

.rd-price {
  font-size: 28rpx;
  color: #FF6B35;
  font-weight: 600;
}

.rd-tags {
  margin-bottom: 16rpx;
}

.rd-tag {
  display: inline-block;
  padding: 4rpx 16rpx;
  background: #f0f0f0;
  border-radius: 8rpx;
  font-size: 24rpx;
  color: #666;
}

.rd-field {
  padding: 16rpx 0;
  border-top: 1rpx solid #f5f5f5;
}

.rd-field-label {
  font-size: 24rpx;
  color: #999;
  display: block;
  margin-bottom: 8rpx;
}

.rd-field-value {
  font-size: 28rpx;
  color: #333;
  line-height: 1.6;
  display: block;
}
</style>
