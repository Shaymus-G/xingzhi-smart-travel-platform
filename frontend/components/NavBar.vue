<script setup lang="ts">
/**
 * 自定义导航栏组件（骨架）
 * 后续可扩展：返回按钮、标题、右侧操作等
 */
interface Props {
  title?: string
  showBack?: boolean
  backgroundColor?: string
}

withDefaults(defineProps<Props>(), {
  title: '行知',
  showBack: false,
  backgroundColor: '#FFFFFF',
})

const emit = defineEmits<{
  back: []
}>()

function handleBack() {
  emit('back')
  uni.navigateBack()
}
</script>

<template>
  <view class="navbar" :style="{ backgroundColor }">
    <view v-if="showBack" class="navbar-back" @tap="handleBack">
      <text class="navbar-back-icon">←</text>
    </view>
    <text class="navbar-title">{{ title }}</text>
    <view class="navbar-placeholder" />
  </view>
</template>

<style lang="scss" scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 88rpx;
  padding: 0 32rpx;
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1rpx solid #eee;
}

.navbar-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #333;
  flex: 1;
  text-align: center;
}

.navbar-back {
  width: 80rpx;
}

.navbar-back-icon {
  font-size: 36rpx;
  color: #333;
}

.navbar-placeholder {
  width: 80rpx;
}
</style>
