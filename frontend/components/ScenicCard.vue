<script setup lang="ts">
/**
 * 景点卡片组件
 * 只负责展示 + emit 点击事件。
 */
import { computed } from 'vue'

interface Props {
  scenicId: number
  name: string
  imageUrl?: string | null
  score?: number | string | null
  price?: number | string | null
  category?: string | null
  address?: string | null
  tagsJson?: unknown
}

const props = withDefaults(defineProps<Props>(), {
  imageUrl: '',
  score: undefined,
  price: undefined,
  category: '',
  address: '',
  tagsJson: undefined,
})

const emit = defineEmits<{
  click: [scenicId: number]
}>()

const FALLBACK_IMAGE = '/static/logo.png'

function getImage(src?: string | null): string {
  return src || FALLBACK_IMAGE
}

/** 格式化为数字显示，兼容 null/undefined/0 */
function formatNum(val?: number | string | null, prefix = '', suffix = ''): string {
  if (val === null || val === undefined || val === '') return ''
  const num = Number(val)
  if (isNaN(num)) return ''
  return `${prefix}${num}${suffix}`
}

const showScore = computed(() => {
  const n = Number(props.score)
  return !isNaN(n) && n > 0 ? '★ ' + n : ''
})

const showPrice = computed(() => formatNum(props.price, '¥'))
</script>

<template>
  <view class="scenic-card" @tap="emit('click', scenicId)">
    <image
      class="scenic-card-image"
      :src="getImage(imageUrl)"
      mode="aspectFill"
    />
    <view class="scenic-card-body">
      <text class="scenic-card-name">{{ name }}</text>
      <view class="scenic-card-tags">
        <text v-if="category" class="scenic-card-tag">{{ category }}</text>
        <text v-if="showScore" class="scenic-card-tag">{{ showScore }}</text>
        <text v-if="showPrice" class="scenic-card-tag">{{ showPrice }}</text>
      </view>
      <text v-if="address" class="scenic-card-address">{{ address }}</text>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.scenic-card {
  display: flex;
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
  margin: 16rpx 0;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.08);
}

.scenic-card-image {
  width: 240rpx;
  height: 180rpx;
  flex-shrink: 0;
  background: #f0f0f0;
}

.scenic-card-body {
  flex: 1;
  padding: 16rpx 20rpx;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.scenic-card-name {
  font-size: 30rpx;
  font-weight: 600;
  color: #333;
  margin-bottom: 8rpx;
}

.scenic-card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-bottom: 6rpx;
}

.scenic-card-tag {
  font-size: 24rpx;
  color: #4A90D9;
  background: rgba(74, 144, 217, 0.1);
  padding: 2rpx 10rpx;
  border-radius: 6rpx;
}

.scenic-card-address {
  font-size: 24rpx;
  color: #999;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
