<script setup lang="ts">
/**
 * 编辑资料页面 — 修改用户名/邮箱/手机/头像/密码/AI API Key
 */
import { ref, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'
import { updateMe } from '@/api/user'
import { useUserStore } from '@/stores/user'
import type { UpdateUserParams } from '@/types/user'

const userStore = useUserStore()

// ========== 表单 ==========
const username = ref('')
const email = ref('')
const phone = ref('')
const avatar = ref('')
const password = ref('')
const apiKey = ref('')
const apiKeyConfigured = ref(false)

// ========== 状态 ==========
const saving = ref(false)

// ========== 初始化 ==========
onMounted(() => {
  if (!userStore.isLoggedIn) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    uni.navigateBack()
    return
  }
  const user = userStore.userInfo
  if (user) {
    username.value = user.username || ''
    email.value = user.email || ''
    phone.value = user.phone || ''
    avatar.value = user.avatar || ''
    // API Key：只显示是否已配置，不显示原文
    apiKeyConfigured.value = !!(user as any).api_key
  }
})

// ========== API Key 掩码 ==========
function apiKeyPlaceholder(): string {
  return apiKeyConfigured.value ? '已配置（输入新值替换）' : '未配置（输入你的 DeepSeek API Key）'
}

// ========== 校验 ==========
function validate(): string | null {
  if (!username.value.trim()) return '用户名不能为空'

  const mail = email.value.trim()
  if (mail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) return '邮箱格式不正确'

  if (phone.value.trim() && !/^\d{7,15}$/.test(phone.value.trim())) return '手机号格式不正确'

  if (password.value && password.value.length < 6) return '密码长度不少于6位'

  return null
}

// ========== 保存 ==========
async function handleSave() {
  const error = validate()
  if (error) {
    uni.showToast({ title: error, icon: 'none' })
    return
  }

  if (saving.value) return
  saving.value = true

  try {
    const data: UpdateUserParams = {}
    const user = userStore.userInfo

    if (username.value.trim() !== (user?.username || '')) data.username = username.value.trim()
    if (email.value.trim() !== (user?.email || '')) data.email = email.value.trim()
    if (phone.value.trim() !== (user?.phone || '')) data.phone = phone.value.trim()
    if (avatar.value.trim() !== (user?.avatar || '')) data.avatar = avatar.value.trim()
    if (password.value) data.password = password.value
    // api_key: 用户输入新值时提交，空值不覆盖已有 Key
    if (apiKey.value.trim()) data.api_key = apiKey.value.trim()

    // 无修改
    if (Object.keys(data).length === 0) {
      uni.showToast({ title: '没有需要保存的修改', icon: 'none' })
      saving.value = false
      return
    }

    const updated = await updateMe(data)
    userStore.userInfo = updated
    // 同步到 storage
    uni.setStorageSync('user_info', JSON.stringify(updated))

    // 清除敏感输入
    password.value = ''
    apiKey.value = ''

    uni.showToast({ title: '保存成功', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 800)
  } catch (err) {
    const msg = err instanceof Error ? err.message : '保存失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <view class="edit-page">
    <NavBar title="编辑资料" :show-back="true" />

    <scroll-view class="edit-scroll" scroll-y>
      <!-- 基本信息 -->
      <view class="edit-section">
        <text class="edit-section-title">基本信息</text>

        <view class="edit-field">
          <text class="edit-label">用户名</text>
          <input v-model="username" class="edit-input" placeholder="用户名" />
        </view>

        <view class="edit-field">
          <text class="edit-label">邮箱</text>
          <input v-model="email" class="edit-input" type="email" placeholder="user@example.com" />
        </view>

        <view class="edit-field">
          <text class="edit-label">手机号</text>
          <input v-model="phone" class="edit-input" type="number" placeholder="手机号" />
        </view>

        <view class="edit-field">
          <text class="edit-label">头像 URL</text>
          <input v-model="avatar" class="edit-input" placeholder="https://..." />
        </view>

        <view class="edit-field">
          <text class="edit-label">新密码</text>
          <input
            v-model="password"
            class="edit-input"
            type="password"
            placeholder="留空表示不修改密码"
          />
        </view>
      </view>

      <!-- AI API Key -->
      <view class="edit-section">
        <text class="edit-section-title">AI API Key</text>
        <text class="edit-section-hint">
          配置你自己的 DeepSeek API Key，用于 AI 对话功能。
          不填写则表示不修改当前配置。
        </text>

        <view class="edit-field">
          <text class="edit-label">Key 状态</text>
          <text :class="apiKeyConfigured ? 'edit-status-ok' : 'edit-status-empty'">
            {{ apiKeyConfigured ? '● 已配置' : '○ 未配置' }}
          </text>
        </view>

        <view class="edit-field">
          <text class="edit-label">新 Key</text>
          <input
            v-model="apiKey"
            class="edit-input"
            :type="apiKey ? 'password' : 'text'"
            :placeholder="apiKeyPlaceholder()"
          />
          <text class="edit-field-hint">
            提交后立即清空输入，不在前端保存明文 Key
          </text>
        </view>
      </view>

      <!-- 保存按钮 -->
      <view class="edit-actions">
        <button
          class="edit-save-btn"
          :loading="saving"
          :disabled="saving"
          @tap="handleSave"
        >
          保存修改
        </button>
      </view>

      <view style="height: 60rpx;" />
    </scroll-view>
  </view>
</template>

<style lang="scss" scoped>
.edit-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.edit-scroll {
  flex: 1;
}

.edit-section {
  background: #fff;
  margin-top: 16rpx;
  padding: 24rpx 32rpx;
}

.edit-section-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 8rpx;
}

.edit-section-hint {
  font-size: 24rpx;
  color: #999;
  line-height: 1.6;
  display: block;
  margin-bottom: 16rpx;
}

.edit-field {
  margin-top: 20rpx;
}

.edit-label {
  font-size: 26rpx;
  color: #666;
  display: block;
  margin-bottom: 8rpx;
}

.edit-input {
  height: 80rpx;
  background: #f7f8fa;
  border-radius: 10rpx;
  padding: 0 20rpx;
  font-size: 28rpx;
}

.edit-field-hint {
  font-size: 22rpx;
  color: #bbb;
  margin-top: 6rpx;
  display: block;
}

.edit-status-ok {
  font-size: 26rpx;
  color: #52C41A;
}

.edit-status-empty {
  font-size: 26rpx;
  color: #ccc;
}

.edit-actions {
  padding: 32rpx;
}

.edit-save-btn {
  height: 88rpx;
  background: #4A90D9;
  color: #fff;
  font-size: 32rpx;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.edit-save-btn[disabled] {
  opacity: 0.7;
}
</style>
