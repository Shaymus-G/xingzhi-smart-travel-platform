<script setup lang="ts">
/**
 * 启动页（欢迎页）
 * 检查登录态 → 已登录跳首页，未登录跳登录页
 */
import { onMounted } from 'vue'
import { getToken } from '@/utils/storage'

onMounted(() => {
  setTimeout(() => {
    const token = getToken()
    if (token) {
      uni.switchTab({ url: '/pages/home/home' })
    } else {
      uni.redirectTo({ url: '/pages/auth/login' })
    }
  }, 500)
})
</script>

<template>
  <view class="splash">
    <image class="splash-logo" src="/static/logo.png" mode="aspectFit" />
    <text class="splash-title">行知</text>
    <text class="splash-subtitle">智慧文旅服务平台</text>
    <view class="splash-loading">
      <text class="splash-loading-text">加载中...</text>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.splash {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: linear-gradient(135deg, #4A90D9, #6BA5E7);
}

.splash-logo {
  width: 160rpx;
  height: 160rpx;
  margin-bottom: 32rpx;
}

.splash-title {
  font-size: 56rpx;
  font-weight: 700;
  color: #fff;
  margin-bottom: 12rpx;
}

.splash-subtitle {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.8);
}

.splash-loading {
  position: absolute;
  bottom: 100rpx;
}

.splash-loading-text {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.6);
}
</style>
