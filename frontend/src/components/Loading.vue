<script setup lang="ts">
/**
 * 全局加载状态组件
 */
interface Props {
  visible?: boolean
  text?: string
}

withDefaults(defineProps<Props>(), {
  visible: false,
  text: '加载中...',
})
</script>

<template>
  <view v-if="visible" class="loading-overlay">
    <view class="loading-spinner" />
    <text class="loading-text">{{ text }}</text>
  </view>
</template>

<style lang="scss" scoped>
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  z-index: 999;
}

.loading-spinner {
  width: 60rpx;
  height: 60rpx;
  border: 4rpx solid #f0f0f0;
  border-top-color: #4A90D9;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-text {
  margin-top: 20rpx;
  font-size: 28rpx;
  color: #999;
}
</style>
