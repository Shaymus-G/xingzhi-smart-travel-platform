<script setup lang="ts">
/**
 * 高级设置页面 — 管理后端 API 地址
 *
 * 支持：
 *  - 查看当前地址及来源
 *  - 修改 API 地址（移动端联调：填写电脑局域网 IP）
 *  - 测试连接（不携带 JWT）
 *  - 恢复默认地址
 *  - 地址变更后自动清除登录态
 */
import { ref, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'
import {
  getApiBaseUrl,
  getDefaultApiBaseUrl,
  setApiBaseUrl,
  resetApiBaseUrl,
  validateApiBaseUrl,
  testApiConnection,
  isApiBaseUrlOverridden,
} from '@/config/runtime'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// ========== 状态 ==========
const currentUrl = ref('')
const defaultUrl = ref('')
const isOverridden = ref(false)
const inputUrl = ref('')
const testing = ref(false)
const testResult = ref<{ ok: boolean; error?: string } | null>(null)

// ========== 初始化 ==========
onMounted(() => {
  refreshState()
})

function refreshState() {
  currentUrl.value = getApiBaseUrl()
  defaultUrl.value = getDefaultApiBaseUrl()
  isOverridden.value = isApiBaseUrlOverridden()
  inputUrl.value = currentUrl.value
  testResult.value = null
}

// ========== 保存 ==========
async function handleSave() {
  const trimmed = inputUrl.value.trim()

  if (!trimmed) {
    uni.showToast({ title: '请输入地址', icon: 'none' })
    return
  }

  const validation = validateApiBaseUrl(trimmed)
  if (!validation.valid) {
    uni.showToast({ title: validation.error || '地址格式不正确', icon: 'none' })
    return
  }

  if (validation.valid && validation.error) {
    // 有警告（如 HTTP 非本地）
    uni.showToast({ title: validation.error, icon: 'none' })
    return
  }

  // 二次确认
  uni.showModal({
    title: '确认修改 API 地址',
    content: `即将切换到：${trimmed}\n\n修改后需要重新登录。`,
    confirmText: '确认切换',
    success(res) {
      if (res.confirm) {
        performSave(trimmed.replace(/\/+$/, ''))
      }
    },
  })
}

function performSave(url: string) {
  setApiBaseUrl(url)
  userStore.logout()
  refreshState()
  testResult.value = null
  uni.showToast({ title: '已切换，请重新登录', icon: 'success' })
}

// ========== 测试连接 ==========
async function handleTest() {
  const url = inputUrl.value.trim().replace(/\/+$/, '')
  if (!url) {
    uni.showToast({ title: '请先输入地址', icon: 'none' })
    return
  }
  testing.value = true
  testResult.value = null
  const result = await testApiConnection(url)
  testResult.value = result
  testing.value = false
  if (result.ok) {
    uni.showToast({ title: '连接成功', icon: 'success' })
  }
}

// ========== 恢复默认 ==========
function handleReset() {
  if (!isOverridden.value) {
    uni.showToast({ title: '当前已是默认地址', icon: 'none' })
    return
  }
  uni.showModal({
    title: '恢复默认地址',
    content: `将恢复到：${defaultUrl.value}\n\n恢复后需要重新登录。`,
    confirmText: '确认恢复',
    success(res) {
      if (res.confirm) {
        resetApiBaseUrl()
        userStore.logout()
        refreshState()
        testResult.value = null
        uni.showToast({ title: '已恢复默认，请重新登录', icon: 'success' })
      }
    },
  })
}
</script>

<template>
  <view class="settings-page">
    <NavBar title="高级设置" :show-back="true" />

    <scroll-view class="settings-scroll" scroll-y>
      <!-- 当前状态 -->
      <view class="settings-section">
        <text class="settings-section-title">当前 API 地址</text>

        <view class="settings-info-card">
          <text class="settings-info-url">{{ currentUrl || '未配置' }}</text>
          <text class="settings-info-source">
            来源：{{ isOverridden ? '本地覆盖' : '环境变量' }}
          </text>
        </view>
      </view>

      <!-- 修改地址 -->
      <view class="settings-section">
        <text class="settings-section-title">修改地址</text>
        <text class="settings-section-hint">
          移动端真机联调：填写电脑局域网 IP（如 http://192.168.1.10:8000），\n
          手机和电脑需连接同一 WiFi，电脑防火墙需放行端口 8000。
        </text>

        <view class="settings-field">
          <input
            v-model="inputUrl"
            class="settings-input"
            placeholder="http://192.168.1.10:8000"
          />
        </view>

        <view class="settings-actions">
          <button
            class="settings-btn settings-btn-test"
            :loading="testing"
            :disabled="testing"
            @tap="handleTest"
          >
            测试连接
          </button>
          <button class="settings-btn settings-btn-save" @tap="handleSave">
            保存地址
          </button>
        </view>

        <!-- 测试结果 -->
        <view v-if="testResult" class="settings-test-result" :class="testResult.ok ? 'ok' : 'fail'">
          <text>{{ testResult.ok ? '✓ 连接成功' : '✗ ' + (testResult.error || '连接失败') }}</text>
        </view>
      </view>

      <!-- 恢复默认 -->
      <view class="settings-section">
        <text class="settings-section-title">恢复默认</text>
        <view class="settings-default-card">
          <text class="settings-default-label">默认地址</text>
          <text class="settings-default-url">{{ defaultUrl || '未配置' }}</text>
        </view>
        <button class="settings-btn settings-btn-reset" @tap="handleReset">
          恢复默认地址
        </button>
      </view>

      <view style="height: 60rpx;" />
    </scroll-view>
  </view>
</template>

<style lang="scss" scoped>
.settings-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.settings-scroll {
  flex: 1;
}

.settings-section {
  background: #fff;
  margin-top: 16rpx;
  padding: 24rpx 32rpx;
}

.settings-section-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 8rpx;
}

.settings-section-hint {
  font-size: 24rpx;
  color: #999;
  line-height: 1.6;
  display: block;
  margin-bottom: 16rpx;
  white-space: pre-line;
}

.settings-info-card {
  background: #f7f8fa;
  border-radius: 10rpx;
  padding: 20rpx;
}

.settings-info-url {
  font-size: 28rpx;
  color: #333;
  word-break: break-all;
}

.settings-info-source {
  font-size: 22rpx;
  color: #999;
  display: block;
  margin-top: 8rpx;
}

.settings-field {
  margin-top: 8rpx;
}

.settings-input {
  height: 80rpx;
  background: #f7f8fa;
  border-radius: 10rpx;
  padding: 0 20rpx;
  font-size: 28rpx;
}

.settings-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 20rpx;
}

.settings-btn {
  flex: 1;
  height: 72rpx;
  font-size: 26rpx;
  border-radius: 10rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.settings-btn-test {
  background: #f0f0f0;
  color: #666;
}

.settings-btn-save {
  background: #4A90D9;
  color: #fff;
}

.settings-btn-reset {
  background: #fff;
  color: #FF4D4F;
  border: 1rpx solid #FF4D4F;
  margin-top: 16rpx;
}

.settings-test-result {
  margin-top: 16rpx;
  padding: 16rpx;
  border-radius: 8rpx;
  font-size: 26rpx;
}

.settings-test-result.ok {
  background: #f0fdf4;
  color: #16a34a;
}

.settings-test-result.fail {
  background: #fef2f2;
  color: #dc2626;
}

.settings-default-card {
  background: #f7f8fa;
  border-radius: 10rpx;
  padding: 20rpx;
}

.settings-default-label {
  font-size: 24rpx;
  color: #999;
}

.settings-default-url {
  font-size: 28rpx;
  color: #333;
  display: block;
  margin-top: 4rpx;
  word-break: break-all;
}
</style>
