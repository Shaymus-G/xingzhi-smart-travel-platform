<script setup lang="ts">
/**
 * AI 旅行计划生成页面
 */
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import NavBar from '@/components/NavBar.vue'
import { generatePlan } from '@/api/ai'

// 偏好标签选项
const PREF_TAGS = [
  '自然风光', '历史文化', '本地美食', '博物馆',
  '亲子', '摄影', '休闲', '户外', '购物', '娱乐',
]

const destination = ref('')
const days = ref(3)
const budget = ref<number | undefined>(undefined)
const travelers = ref(1)
const selectedPrefs = ref<string[]>([])
const startDate = ref('')
const notes = ref('')
const isGenerating = ref(false)

// ========== 预填（从重新生成入口进入） ==========

onLoad((options: any) => {
  if (options?.from !== 'regenerate') return

  // destination
  if (options.destination) {
    destination.value = safeDecodeURIComponent(options.destination)
  }

  // days
  const d = parseIntegerInRange(options.days, 1, 10)
  if (d !== null) days.value = d

  // budget
  if (options.budget !== undefined && options.budget !== null && String(options.budget) !== '') {
    const b = Number(options.budget)
    if (Number.isFinite(b) && b >= 0) budget.value = b
  }

  // travelers
  const t = parseIntegerInRange(options.travelers, 1, 20)
  if (t !== null) travelers.value = t
})

// ========== 辅助函数 ==========

function safeDecodeURIComponent(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function parseIntegerInRange(value: unknown, min: number, max: number): number | null {
  if (value === undefined || value === null) return null
  const n = Number(value)
  if (!Number.isFinite(n) || !Number.isInteger(n)) return null
  if (n < min || n > max) return null
  return n
}

// ========== 表单操作 ==========

function togglePref(tag: string) {
  const idx = selectedPrefs.value.indexOf(tag)
  if (idx >= 0) {
    selectedPrefs.value.splice(idx, 1)
  } else {
    if (selectedPrefs.value.length < 10) {
      selectedPrefs.value.push(tag)
    }
  }
}

async function handleGenerate() {
  const dest = destination.value.trim()
  if (!dest) {
    uni.showToast({ title: '请输入目的地', icon: 'none' })
    return
  }
  if (days.value < 1 || days.value > 10) {
    uni.showToast({ title: '天数需在 1-10 之间', icon: 'none' })
    return
  }
  if (isGenerating.value) return

  isGenerating.value = true

  try {
    const plan = await generatePlan({
      destination: dest,
      days: days.value,
      budget: budget.value || undefined,
      travelers: travelers.value,
      preferences: selectedPrefs.value.length > 0 ? selectedPrefs.value : undefined,
      start_date: startDate.value || undefined,
      notes: notes.value.trim() || undefined,
    })

    uni.showToast({ title: '计划生成成功！', icon: 'success' })
    // 跳转到详情页
    uni.redirectTo({ url: `/pages/plan/detail?id=${plan.id}` })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '生成失败，请稍后重试'
    uni.showToast({ title: msg, icon: 'none', duration: 3000 })
  } finally {
    isGenerating.value = false
  }
}
</script>

<template>
  <view class="generate-page">
    <NavBar title="AI 生成计划" :show-back="true" />

    <scroll-view class="form-scroll" scroll-y>
      <!-- 目的地 -->
      <view class="form-group">
        <text class="form-label">目的地 <text class="required">*</text></text>
        <input
          v-model="destination"
          class="form-input"
          placeholder="例如：杭州、成都、北京"
          :disabled="isGenerating"
        />
      </view>

      <!-- 天数 -->
      <view class="form-group">
        <text class="form-label">天数 <text class="required">*</text></text>
        <view class="stepper-row">
          <button class="stepper-btn" :disabled="days <= 1 || isGenerating" @tap="days--">-</button>
          <text class="stepper-value">{{ days }}</text>
          <button class="stepper-btn" :disabled="days >= 10 || isGenerating" @tap="days++">+</button>
        </view>
      </view>

      <!-- 预算 -->
      <view class="form-group">
        <text class="form-label">预算（元）</text>
        <input
          v-model="budget"
          class="form-input"
          type="digit"
          placeholder="例如：3000（总预算，可不填）"
          :disabled="isGenerating"
        />
      </view>

      <!-- 人数 -->
      <view class="form-group">
        <text class="form-label">出行人数</text>
        <view class="stepper-row">
          <button class="stepper-btn" :disabled="travelers <= 1 || isGenerating" @tap="travelers--">-</button>
          <text class="stepper-value">{{ travelers }}</text>
          <button class="stepper-btn" :disabled="travelers >= 20 || isGenerating" @tap="travelers++">+</button>
        </view>
      </view>

      <!-- 兴趣偏好 -->
      <view class="form-group">
        <text class="form-label">兴趣偏好（可多选）</text>
        <view class="tag-grid">
          <view
            v-for="tag in PREF_TAGS"
            :key="tag"
            class="pref-tag"
            :class="{ active: selectedPrefs.includes(tag) }"
            @tap="togglePref(tag)"
          >
            <text>{{ tag }}</text>
          </view>
        </view>
      </view>

      <!-- 出行日期 -->
      <view class="form-group">
        <text class="form-label">出行日期</text>
        <picker
          mode="date"
          :value="startDate"
          :disabled="isGenerating"
          @change="(e: any) => startDate = e.detail.value"
        >
          <view class="form-input picker-input">
            <text :class="{ placeholder: !startDate }">
              {{ startDate || '可不填，选择日期' }}
            </text>
          </view>
        </picker>
      </view>

      <!-- 补充要求 -->
      <view class="form-group">
        <text class="form-label">补充要求</text>
        <textarea
          v-model="notes"
          class="form-textarea"
          placeholder="例如：节奏适中、少走回头路、避免太早出发"
          :maxlength="1000"
          :disabled="isGenerating"
        />
        <text class="char-count">{{ notes.length }}/1000</text>
      </view>
    </scroll-view>

    <!-- 生成按钮 -->
    <view class="bottom-bar safe-area-bottom">
      <button
        class="generate-btn"
        :disabled="!destination.trim() || isGenerating"
        @tap="handleGenerate"
      >
        <text v-if="isGenerating">AI 正在生成行程，可能需要几十秒...</text>
        <text v-else>开始生成</text>
      </button>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.generate-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.form-scroll {
  flex: 1;
  padding: 24rpx 32rpx;
}

.form-group {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.form-label {
  font-size: 28rpx;
  color: #333;
  font-weight: 600;
  margin-bottom: 16rpx;
  display: block;
}

.required {
  color: #FF6B35;
}

.form-input {
  height: 72rpx;
  background: #f8f8f8;
  border-radius: 12rpx;
  padding: 0 20rpx;
  font-size: 28rpx;
}

.picker-input {
  display: flex;
  align-items: center;
}

.placeholder {
  color: #ccc;
}

.stepper-row {
  display: flex;
  align-items: center;
  gap: 24rpx;
}

.stepper-btn {
  width: 64rpx;
  height: 64rpx;
  border-radius: 32rpx;
  background: #f0f0f0;
  color: #333;
  font-size: 32rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
}

.stepper-btn[disabled] {
  opacity: 0.4;
}

.stepper-value {
  font-size: 32rpx;
  font-weight: 700;
  min-width: 60rpx;
  text-align: center;
}

.tag-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.pref-tag {
  padding: 12rpx 24rpx;
  border-radius: 32rpx;
  background: #f0f0f0;
  font-size: 26rpx;
  color: #666;
  border: 2rpx solid transparent;
}

.pref-tag.active {
  background: #e8f0fe;
  color: #4A90D9;
  border-color: #4A90D9;
}

.form-textarea {
  width: 100%;
  min-height: 160rpx;
  background: #f8f8f8;
  border-radius: 12rpx;
  padding: 20rpx;
  font-size: 28rpx;
  box-sizing: border-box;
}

.char-count {
  font-size: 24rpx;
  color: #bbb;
  text-align: right;
  display: block;
  margin-top: 8rpx;
}

.bottom-bar {
  padding: 20rpx 32rpx;
  background: #fff;
  border-top: 1rpx solid #eee;
}

.generate-btn {
  width: 100%;
  height: 88rpx;
  background: #4A90D9;
  color: #fff;
  font-size: 32rpx;
  border-radius: 44rpx;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

.generate-btn[disabled] {
  background: #ccc;
}
</style>
