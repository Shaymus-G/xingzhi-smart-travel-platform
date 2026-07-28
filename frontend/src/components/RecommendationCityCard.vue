<script setup lang="ts">
/**
 * 推荐城市卡片组件
 *
 * 只负责展示推荐城市信息 + emit 点击事件，不负责导航。
 * 图片复用 SafeImage，文本截断使用 CSS。
 */
import { computed } from 'vue'
import SafeImage from '@/components/SafeImage.vue'
import {
  formatDistanceKm,
  formatRecommendScore,
  normalizeRecommendReason,
} from '@/utils/recommend'
import type { NormalizedRecommendCity, RecommendationVariant } from '@/types/recommend'

// ==================== Props ====================

interface Props {
  city: NormalizedRecommendCity
  variant: RecommendationVariant
}

const props = defineProps<Props>()

// ==================== Emits ====================

const emit = defineEmits<{
  (e: 'click', cityId: number): void
}>()

// ==================== 点击安全 ====================

function handleTap(): void {
  const { id } = props.city
  if (!Number.isFinite(id) || !Number.isInteger(id) || id <= 0) return
  emit('click', id)
}

// ==================== 展示内容 ====================

/** 格式化后的距离文本 */
const distanceText = computed(() => formatDistanceKm(props.city.distanceKm))

/** 格式化后的评分文本 */
const scoreText = computed(() => {
  const s = formatRecommendScore(props.city.score)
  return s ? `推荐度 ${s}` : ''
})

/** 标准化后的推荐理由 */
const reasonText = computed(() => normalizeRecommendReason(props.city.reason))

/** 是否有 level 标签 */
const hasLevel = computed(() => {
  const lv = props.city.level
  return lv !== null && lv !== ''
})

/**
 * 根据 variant 确定展示内容
 *
 * nearby:      城市名 + level + distance
 * similar:     城市名 + province(→level) + reason
 * contrast:    城市名 + level + reason
 * collaborative: 城市名 + (reason → score → province → level)
 */

/** 标题行：是否显示 level 标签 */
const showLevel = computed(() => {
  if (props.variant === 'similar') return false
  return hasLevel.value
})

/** 元信息行文案 */
const metaText = computed(() => {
  switch (props.variant) {
    case 'nearby':
      return distanceText.value
    case 'similar': {
      const p = props.city.province
      if (p !== null && p !== '') return p
      const lv = props.city.level
      return lv !== null && lv !== '' ? lv : ''
    }
    case 'contrast':
      return ''
    case 'collaborative': {
      // 降级顺序：reason → score → province → level
      const r = reasonText.value
      if (r) return r
      const s = scoreText.value
      if (s) return s
      const p = props.city.province
      if (p !== null && p !== '') return p
      const lv = props.city.level
      return lv !== null && lv !== '' ? lv : ''
    }
    default:
      return ''
  }
})

/** 推荐原因行文案（仅 similar / contrast 独立显示） */
const reasonLine = computed(() => {
  if (props.variant === 'similar' || props.variant === 'contrast') {
    return reasonText.value
  }
  return ''
})
</script>

<template>
  <view class="rc-card" @tap.stop="handleTap">
    <SafeImage
      class="rc-card-image"
      :src="city.coverImage"
      mode="aspectFill"
    />
    <view class="rc-card-body">
      <!-- 标题行：城市名 + level 标签 -->
      <view class="rc-card-header">
        <text v-if="city.name" class="rc-card-name">{{ city.name }}</text>
        <text v-if="showLevel" class="rc-card-level">{{ city.level }}</text>
      </view>
      <!-- 元信息行 -->
      <text v-if="metaText" class="rc-card-meta">{{ metaText }}</text>
      <!-- 推荐原因行 -->
      <text v-if="reasonLine" class="rc-card-reason">{{ reasonLine }}</text>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.rc-card {
  width: 280rpx;
  flex-shrink: 0;
  overflow: hidden;
  box-sizing: border-box;
  background: #fff;
  border-radius: 12rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.08);
}

.rc-card-image {
  width: 100%;
  height: 180rpx;
  background: #f0f0f0;
}

.rc-card-body {
  padding: 16rpx;
}

.rc-card-header {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.rc-card-name {
  min-width: 0;
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rc-card-level {
  font-size: 22rpx;
  color: #4A90D9;
  background: rgba(74, 144, 217, 0.1);
  padding: 2rpx 10rpx;
  border-radius: 6rpx;
  flex-shrink: 0;
}

.rc-card-meta {
  display: block;
  font-size: 24rpx;
  color: #666;
  margin-top: 6rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rc-card-reason {
  display: block;
  font-size: 22rpx;
  color: #999;
  margin-top: 4rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
