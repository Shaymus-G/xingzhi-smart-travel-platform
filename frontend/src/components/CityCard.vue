<script setup lang="ts">
/**
 * 城市卡片组件（骨架）
 * 后续接入真实数据时替换占位内容
 */
interface Props {
  cityId: number
  name: string
  province?: string
  coverImage?: string
  level?: string
  description?: string
}

withDefaults(defineProps<Props>(), {
  province: '',
  coverImage: '',
  level: '普通',
  description: '',
})

const emit = defineEmits<{
  click: [cityId: number]
}>()

function handleClick(cityId: number) {
  emit('click', cityId)
  uni.navigateTo({ url: `/pages/city/detail?id=${cityId}` })
}
</script>

<template>
  <view class="city-card" @tap="handleClick(cityId)">
    <image
      class="city-card-image"
      :src="coverImage || '/static/logo.png'"
      mode="aspectFill"
    />
    <view class="city-card-info">
      <view class="city-card-header">
        <text class="city-card-name">{{ name }}</text>
        <text class="city-card-level">{{ level }}</text>
      </view>
      <text v-if="province" class="city-card-province">{{ province }}</text>
      <text v-if="description" class="city-card-desc">{{ description }}</text>
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
