<script setup lang="ts">
/**
 * 登录页面
 * 对接后端 POST /api/users/login
 */
import { ref } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const username = ref('')
const password = ref('')
const loading = ref(false)

/** 表单校验 */
function validate(): string | null {
  if (!username.value.trim()) return '请输入用户名'
  if (!password.value) return '请输入密码'
  if (password.value.length < 6) return '密码长度不少于6位'
  return null
}

/** 登录 */
async function handleLogin() {
  const error = validate()
  if (error) {
    uni.showToast({ title: error, icon: 'none' })
    return
  }

  loading.value = true
  try {
    await userStore.loginAction({
      username: username.value.trim(),
      password: password.value,
    })
    uni.showToast({ title: '登录成功', icon: 'success' })
    // 延迟跳转，让 toast 展示出来
    setTimeout(() => {
      uni.switchTab({ url: '/pages/home/home' })
    }, 800)
  } catch (err) {
    const msg = err instanceof Error ? err.message : '登录失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    loading.value = false
  }
}

/** 跳转注册页 */
function goRegister() {
  uni.navigateTo({ url: '/pages/auth/register' })
}
</script>

<template>
  <view class="auth-page">
    <view class="auth-header">
      <image class="auth-logo" src="/static/logo.png" mode="aspectFit" />
      <text class="auth-title">行知</text>
      <text class="auth-subtitle">欢迎回来</text>
    </view>

    <view class="auth-form">
      <input
        v-model="username"
        class="auth-input"
        placeholder="请输入用户名"
        placeholder-style="color: #ccc;"
      />
      <input
        v-model="password"
        class="auth-input"
        type="password"
        placeholder="请输入密码"
        placeholder-style="color: #ccc;"
      />

      <button class="auth-btn" :loading="loading" :disabled="loading" @tap="handleLogin">
        登录
      </button>

      <view class="auth-footer">
        <text>还没有账号？</text>
        <text class="auth-link" @tap="goRegister">立即注册</text>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.auth-page {
  min-height: 100vh;
  background: #fff;
  padding: 80rpx 48rpx 0;
}

.auth-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 60rpx;
}

.auth-logo {
  width: 120rpx;
  height: 120rpx;
  margin-bottom: 24rpx;
}

.auth-title {
  font-size: 44rpx;
  font-weight: 700;
  color: #4A90D9;
}

.auth-subtitle {
  margin-top: 12rpx;
  font-size: 28rpx;
  color: #999;
}

.auth-form {
  display: flex;
  flex-direction: column;
}

.auth-input {
  height: 88rpx;
  background: #f7f8fa;
  border-radius: 12rpx;
  padding: 0 24rpx;
  font-size: 30rpx;
  margin-bottom: 24rpx;
}

.auth-btn {
  height: 88rpx;
  background: #4A90D9;
  color: #fff;
  font-size: 32rpx;
  border-radius: 12rpx;
  margin-top: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-btn[disabled] {
  opacity: 0.7;
}

.auth-footer {
  display: flex;
  justify-content: center;
  margin-top: 32rpx;
  font-size: 26rpx;
  color: #999;
}

.auth-link {
  color: #4A90D9;
  margin-left: 8rpx;
}
</style>
