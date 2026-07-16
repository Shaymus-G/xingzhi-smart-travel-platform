<script setup lang="ts">
/**
 * 城市卡片组件
 * 只负责展示 + emit 点击事件，不写死跳转路径。
 */
interface Props {
  cityId: number
  name: string
  province?: string | null
  coverImage?: string | null
  level?: string | null
  description?: string | null
}

withDefaults(defineProps<Props>(), {
  province: '',
  coverImage: '',
  level: '',
  description: '',
})

const emit = defineEmits<{
  click: [cityId: number]
}>()

/** 图片兜底 */
const FALLBACK_IMAGE = '/static/logo.png'

function getImage(src?: string | null): string {
  return src || FALLBACK_IMAGE
}

/** 截断描述 */
function truncate(text?: string | null, max = 50): string {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '...' : text
}
</script>

<template>
  <view class="city-card" @tap="emit('click', cityId)">
    <image
      class="city-card-image"
      :src="getImage(coverImage)"
      mode="aspectFill"
    />
    <view class="city-card-info">
      <view class="city-card-header">
        <text class="city-card-name">{{ name }}</text>
        <text v-if="level" class="city-card-level">{{ level }}</text>
      </view>
      <text v-if="province" class="city-card-province">{{ province }}</text>
      <text v-if="description" class="city-card-desc">{{ truncate(description) }}</text>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.city-card {
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
  margin: 16rpx 32rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.08);
}

.city-card-image {
  width: 100%;
  height: 320rpx;
  background: #f0f0f0;
}

.city-card-info {
  padding: 20rpx 24rpx;
}

.city-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8rpx;
}

.city-card-name {
  font-size: 34rpx;
  font-weight: 600;
  color: #333;
}

.city-card-level {
  font-size: 24rpx;
  color: #4A90D9;
  background: rgba(74, 144, 217, 0.1);
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
}

.city-card-province {
  font-size: 26rpx;
  color: #666;
}

.city-card-desc {
  font-size: 26rpx;
  color: #999;
  margin-top: 8rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
