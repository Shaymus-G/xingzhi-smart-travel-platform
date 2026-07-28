<script setup lang="ts">
/**
 * 推荐区域组件
 *
 * 纯展示：标题 + loading/error/数据状态 + 横向滚动卡片列表。
 * 不管理 API 请求、不做数据标准化、不执行导航。
 */
import { computed } from 'vue'
import RecommendationCityCard from '@/components/RecommendationCityCard.vue'
import type { NormalizedRecommendCity, RecommendationVariant } from '@/types/recommend'

// ==================== Props ====================

interface Props {
  title: string
  cities: NormalizedRecommendCity[]
  variant: RecommendationVariant
  loading?: boolean
  error?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
})

// ==================== Emits ====================

const emit = defineEmits<{
  (e: 'click', cityId: number): void
  (e: 'retry'): void
}>()

// ==================== 显示控制 ====================

/** 是否有有效错误信息 */
const hasError = computed(() => {
  const err = props.error
  return typeof err === 'string' && err.trim().length > 0
})

/** 是否应该渲染整个 Section */
const shouldRender = computed(() => {
  return props.loading || hasError.value || props.cities.length > 0
})

// ==================== 事件转发 ====================

function handleCardClick(cityId: number): void {
  emit('click', cityId)
}

function handleRetry(): void {
  emit('retry')
}
</script>

<template>
  <view v-if="shouldRender" class="rs-section">
    <!-- 标题 -->
    <view class="rs-section-header">
      <text class="rs-section-title">{{ title }}</text>
    </view>

    <!-- Loading -->
    <view v-if="loading" class="rs-status">
      <text class="rs-status-text">加载中...</text>
    </view>

    <!-- Error -->
    <view v-else-if="hasError" class="rs-status rs-status-error">
      <text class="rs-status-text">{{ error }}</text>
      <view class="rs-retry-btn" @tap="handleRetry">
        <text>重新加载</text>
      </view>
    </view>

    <!-- 横向卡片列表 -->
    <scroll-view
      v-else-if="cities.length > 0"
      scroll-x
      :show-scrollbar="false"
      enable-flex
      class="rs-scroll"
    >
      <view class="rs-list">
        <view
          v-for="city in cities"
          :key="`${variant}-${city.id}`"
          class="rs-card-wrapper"
        >
          <RecommendationCityCard
            :city="city"
            :variant="variant"
            @click="handleCardClick"
          />
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<style lang="scss" scoped>
.rs-section {
  margin-top: 8rpx;
  padding: 24rpx 0;
}

.rs-section-header {
  padding: 0 32rpx 16rpx;
}

.rs-section-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #333;
}

// ==================== Loading / Error ====================

.rs-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32rpx 32rpx;
}

.rs-status-text {
  font-size: 26rpx;
  color: #999;
}

.rs-status-error .rs-status-text {
  color: #d93025;
}

.rs-retry-btn {
  margin-top: 16rpx;
  padding: 10rpx 36rpx;
  border: 1px solid #4A90D9;
  border-radius: 24rpx;
  font-size: 26rpx;
  color: #4A90D9;
}

// ==================== 横向滚动 ====================

.rs-scroll {
  width: 100%;
}

.rs-list {
  display: flex;
  flex-direction: row;
  padding: 0 32rpx;
}

.rs-card-wrapper {
  flex-shrink: 0;
  margin-right: 16rpx;
}
</style>
