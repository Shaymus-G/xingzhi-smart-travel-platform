<script setup lang="ts">
/**
 * 注册页面
 * 对接后端 POST /api/users/register
 */
import { ref } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)

/** 简单邮箱格式校验 */
function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
}

/** 表单校验 */
function validate(): string | null {
  if (!username.value.trim()) return '请输入用户名'
  if (!email.value.trim()) return '请输入邮箱'
  if (!isValidEmail(email.value.trim())) return '邮箱格式不正确'
  if (!password.value) return '请输入密码'
  if (password.value.length < 6) return '密码长度不少于6位'
  if (password.value !== confirmPassword.value) return '两次密码不一致'
  return null
}

/** 注册 */
async function handleRegister() {
  const error = validate()
  if (error) {
    uni.showToast({ title: error, icon: 'none' })
    return
  }

  loading.value = true
  try {
    await userStore.registerAction({
      username: username.value.trim(),
      email: email.value.trim(),
      password: password.value,
    })
    uni.showToast({ title: '注册成功，请登录', icon: 'success' })
    setTimeout(() => {
      uni.redirectTo({ url: '/pages/auth/login' })
    }, 1000)
  } catch (err) {
    const msg = err instanceof Error ? err.message : '注册失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    loading.value = false
  }
}

/** 返回登录页 */
function goLogin() {
  uni.navigateBack()
}
</script>

<template>
  <view class="auth-page">
    <view class="auth-header">
      <text class="auth-title">注册账号</text>
      <text class="auth-subtitle">加入行知，开启智慧旅行</text>
    </view>

    <view class="auth-form">
      <input
        v-model="username"
        class="auth-input"
        placeholder="用户名"
        placeholder-style="color: #ccc;"
      />
      <input
        v-model="email"
        class="auth-input"
        type="email"
        placeholder="邮箱"
        placeholder-style="color: #ccc;"
      />
      <input
        v-model="password"
        class="auth-input"
        type="password"
        placeholder="密码（至少6位）"
        placeholder-style="color: #ccc;"
      />
      <input
        v-model="confirmPassword"
        class="auth-input"
        type="password"
        placeholder="确认密码"
        placeholder-style="color: #ccc;"
      />

      <button class="auth-btn" :loading="loading" :disabled="loading" @tap="handleRegister">
        注册
      </button>

      <view class="auth-footer">
        <text>已有账号？</text>
        <text class="auth-link" @tap="goLogin">返回登录</text>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.auth-page {
  min-height: 100vh;
  background: #fff;
  padding: 60rpx 48rpx 0;
}

.auth-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 48rpx;
}

.auth-title {
  font-size: 40rpx;
  font-weight: 700;
  color: #333;
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
  margin-bottom: 20rpx;
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
