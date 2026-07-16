<script setup lang="ts">
/**
 * 景点卡片组件（骨架）
 */
interface Props {
  scenicId: number
  name: string
  imageUrl?: string
  score?: number
  price?: number
  category?: string
  address?: string
}

withDefaults(defineProps<Props>(), {
  imageUrl: '',
  score: 0,
  price: 0,
  category: '',
  address: '',
})

const emit = defineEmits<{
  click: [scenicId: number]
}>()

function handleClick(scenicId: number) {
  emit('click', scenicId)
  uni.navigateTo({ url: `/pages/scenic/detail?id=${scenicId}` })
}
</script>

<template>
  <view class="scenic-card" @tap="handleClick(scenicId)">
    <image
      class="scenic-card-image"
      :src="imageUrl || '/static/logo.png'"
      mode="aspectFill"
    />
    <view class="scenic-card-body">
      <text class="scenic-card-name">{{ name }}</text>
      <view class="scenic-card-tags">
        <text v-if="category" class="scenic-card-tag">{{ category }}</text>
        <text class="scenic-card-tag" v-if="score > 0">★ {{ score }}</text>
        <text class="scenic-card-tag" v-if="price > 0">¥{{ price }}</text>
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
  margin: 16rpx 32rpx;
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
