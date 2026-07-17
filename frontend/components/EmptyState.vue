<script setup lang="ts">
/**
 * 空状态占位组件
 */
interface Props {
  text?: string
  subText?: string
}

withDefaults(defineProps<Props>(), {
  text: '暂无数据',
  subText: '',
})
</script>

<template>
  <view class="empty-state">
    <text class="empty-state-icon">📭</text>
    <text class="empty-state-text">{{ text }}</text>
    <text v-if="subText" class="empty-state-sub">{{ subText }}</text>
  </view>
</template>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 100rpx 32rpx;
}

.empty-state-icon {
  font-size: 80rpx;
  margin-bottom: 24rpx;
}

.empty-state-text {
  font-size: 28rpx;
  color: #999;
}

.empty-state-sub {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #bbb;
}
</style>
