<script setup lang="ts">
/**
 * AI 旅行计划生成页面
 *
 * 状态机：
 *   idle → submitting → generating → success (跳转详情)
 *                    → (超时) confirming → success (匹配到计划)
 *                                        → uncertain (无法确认)
 *   idle → (锁冲突) → 提示已有进行中的生成
 *
 * 防重复：运行时锁 + storage 短期锁（10 分钟自动过期）
 */
import { ref, computed } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import NavBar from '@/components/NavBar.vue'
import { generatePlan, AI_PLAN_GENERATE_TIMEOUT } from '@/api/ai'
import { getMyPlans } from '@/api/travel'
import { ApiError } from '@/api/request'
import type { TravelPlan } from '@/types/travel'

// ==================== 常量 ====================

const PREF_TAGS = [
  '自然风光', '历史文化', '本地美食', '博物馆',
  '亲子', '摄影', '休闲', '户外', '购物', '娱乐',
]

/** 超时后确认轮询：6 次 × 5 秒 = 最多 30 秒 */
const RECONCILE_MAX_ATTEMPTS = 6
const RECONCILE_INTERVAL_MS = 5000
/** Storage 生成锁有效期 10 分钟 */
const LOCK_TTL_MS = 10 * 60 * 1000
const LOCK_STORAGE_KEY = 'XINGZHI_PLAN_GENERATE_LOCK'

// ==================== 状态机类型 ====================

type GenerateStatus =
  | 'idle'        // 未提交
  | 'submitting'  // 请求发出中
  | 'generating'  // 等待后端响应
  | 'confirming'  // 超时，正在通过列表确认
  | 'success'     // 已确认成功
  | 'uncertain'   // 确认耗尽，无法判定
  | 'failed'      // 已确认失败（网络/业务错误/401）

// ==================== 表单状态 ====================

const destination = ref('')
const days = ref(3)
const budget = ref<number | undefined>(undefined)
const travelers = ref(1)
const selectedPrefs = ref<string[]>([])
const startDate = ref('')
const notes = ref('')

const generateStatus = ref<GenerateStatus>('idle')
const statusMessage = ref('')
const reconcileAttempt = ref(0)

// ==================== 生成上下文 ====================

interface GenerateContext {
  submitTime: number
  destination: string
  days: number
  startDate: string
  travelers: number
  fingerprint: string
  baselinePlanIds: Set<number>
  baselineHasError: boolean  // 基线查询异常 → 降低匹配置信度
}

let ctx: GenerateContext | null = null

// ==================== 竞态控制 ====================

let _active = true         // 页面是否存活
let _genVersion = 0        // 生成请求序号
let _reconcileTimer: ReturnType<typeof setTimeout> | null = null

// ==================== 计算属性 ====================

const isBusy = computed(() =>
  generateStatus.value === 'submitting' ||
  generateStatus.value === 'generating' ||
  generateStatus.value === 'confirming',
)

const buttonText = computed(() => {
  switch (generateStatus.value) {
    case 'submitting': return '正在提交……'
    case 'generating': return 'AI 正在生成计划，可能需要较长时间……'
    case 'confirming': return `正在确认结果……(${reconcileAttempt.value}/${RECONCILE_MAX_ATTEMPTS})`
    case 'success': return '生成成功！'
    default: return '开始生成'
  }
})

// ==================== Storage 锁管理 ====================

interface GenerateLock {
  fingerprint: string
  submitTime: number
  expiresAt: number
}

function readLock(): GenerateLock | null {
  try {
    const raw = uni.getStorageSync(LOCK_STORAGE_KEY)
    if (!raw) return null
    const lock = JSON.parse(raw) as GenerateLock
    if (Date.now() > lock.expiresAt) {
      uni.removeStorageSync(LOCK_STORAGE_KEY)
      return null
    }
    return lock
  } catch {
    return null
  }
}

function writeLock(lock: GenerateLock): void {
  try {
    uni.setStorageSync(LOCK_STORAGE_KEY, JSON.stringify(lock))
  } catch {
    // storage 不可用时静默降级
  }
}

function clearLock(): void {
  try {
    uni.removeStorageSync(LOCK_STORAGE_KEY)
  } catch {
    // 静默
  }
}

// ==================== 指纹 ====================

function buildFingerprint(): string {
  return [
    destination.value.trim(),
    String(days.value),
    startDate.value || '',
    String(travelers.value),
  ].join('|')
}

// ==================== 提交前基线 ====================

async function captureBaseline(): Promise<void> {
  try {
    const plans = await getMyPlans({ skip: 0, limit: 50 })
    const ids = new Set<number>()
    if (Array.isArray(plans)) {
      for (const p of plans) {
        if (p && typeof p.id === 'number' && p.id > 0) {
          ids.add(p.id)
        }
      }
    }
    if (ctx) {
      ctx.baselinePlanIds = ids
      ctx.baselineHasError = false
    }
  } catch {
    if (ctx) {
      ctx.baselinePlanIds = new Set()
      ctx.baselineHasError = true
    }
  }
}

// ==================== 表单操作 ====================

function togglePref(tag: string) {
  if (isBusy.value) return
  const idx = selectedPrefs.value.indexOf(tag)
  if (idx >= 0) {
    selectedPrefs.value.splice(idx, 1)
  } else {
    if (selectedPrefs.value.length < 10) {
      selectedPrefs.value.push(tag)
    }
  }
}

// ==================== 锁冲突处理 ====================

function checkExistingLock(): boolean {
  const lock = readLock()
  if (!lock) return false

  const currentFingerprint = buildFingerprint()
  if (lock.fingerprint === currentFingerprint) {
    // 相同参数的生成可能仍在进行
    uni.showModal({
      title: '生成进行中',
      content: '相同旅行计划可能仍在生成，请先前往计划列表查看。是否仍要重新生成？',
      confirmText: '仍要生成',
      cancelText: '前往列表',
      success(res) {
        if (res.confirm) {
          clearLock()
          void doGenerate()
        } else {
          goToPlanList()
        }
      },
    })
    return true
  }

  // 不同参数 — 清理旧锁
  clearLock()
  return false
}

// ==================== 主生成流程 ====================

async function handleGenerate(): Promise<void> {
  if (isBusy.value) return

  const dest = destination.value.trim()
  if (!dest) {
    uni.showToast({ title: '请输入目的地', icon: 'none' })
    return
  }
  if (days.value < 1 || days.value > 10) {
    uni.showToast({ title: '天数需在 1-10 之间', icon: 'none' })
    return
  }

  // 检查 storage 锁
  if (checkExistingLock()) return

  await doGenerate()
}

async function doGenerate(): Promise<void> {
  _genVersion++
  const version = _genVersion

  const dest = destination.value.trim()

  // 记录上下文
  ctx = {
    submitTime: Date.now(),
    destination: dest,
    days: days.value,
    startDate: startDate.value || '',
    travelers: travelers.value,
    fingerprint: buildFingerprint(),
    baselinePlanIds: new Set(),
    baselineHasError: false,
  }

  // 写入 storage 锁
  writeLock({
    fingerprint: ctx.fingerprint,
    submitTime: ctx.submitTime,
    expiresAt: ctx.submitTime + LOCK_TTL_MS,
  })

  // 捕获基线（失败不阻塞提交）
  generateStatus.value = 'submitting'
  await captureBaseline()

  if (version !== _genVersion || !_active) return

  generateStatus.value = 'generating'
  statusMessage.value = ''

  if (import.meta.env.DEV) {
    console.log('[plan-generate] request started', {
      destination: dest,
      days: days.value,
      timeout: AI_PLAN_GENERATE_TIMEOUT,
    })
  }

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

    if (version !== _genVersion || !_active) return

    // 成功响应
    if (import.meta.env.DEV) {
      console.log('[plan-generate] success, planId:', plan.id)
    }
    generateStatus.value = 'success'
    clearLock()
    uni.showToast({ title: '计划生成成功！', icon: 'success' })
    uni.redirectTo({ url: `/pages/plan/detail?id=${plan.id}` })
  } catch (err: unknown) {
    if (version !== _genVersion || !_active) return
    await handleGenerateError(err, version)
  }
}

// ==================== 错误分类与处理 ====================

async function handleGenerateError(err: unknown, version: number): Promise<void> {
  // 401 — 使用现有统一流程（request.ts 已处理 reLaunch）
  if (err instanceof ApiError && err.code === 'AUTH_EXPIRED') {
    generateStatus.value = 'failed'
    statusMessage.value = ''
    clearLock()
    return
  }

  // 请求超时 → 进入确认流程
  if (err instanceof ApiError && err.code === 'REQUEST_TIMEOUT') {
    if (import.meta.env.DEV) {
      console.log('[plan-generate] request timeout, begin reconciliation')
    }
    generateStatus.value = 'confirming'
    statusMessage.value = 'AI 生成耗时较长，正在确认结果……'
    void startReconciliation(version)
    return
  }

  // 网络不可达
  if (err instanceof ApiError && err.code === 'NETWORK_ERROR') {
    generateStatus.value = 'failed'
    statusMessage.value = ''
    clearLock()
    uni.showToast({ title: err.message, icon: 'none', duration: 3000 })
    return
  }

  // 后端业务错误
  if (err instanceof ApiError && err.code === 'BUSINESS_ERROR') {
    generateStatus.value = 'failed'
    statusMessage.value = ''
    clearLock()
    uni.showToast({ title: err.message, icon: 'none', duration: 3000 })
    return
  }

  // 未知错误
  const msg = err instanceof Error ? err.message : '生成失败，请稍后重试'
  generateStatus.value = 'failed'
  statusMessage.value = ''
  clearLock()
  uni.showToast({ title: msg, icon: 'none', duration: 3000 })
}

// ==================== 超时结果确认 ====================

async function startReconciliation(version: number): Promise<void> {
  reconcileAttempt.value = 0
  // 初次等待 3 秒再开始查询（给后端一点额外时间）
  await sleep(3000)
  if (version !== _genVersion || !_active) return
  void reconcileLoop(version)
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => {
    _reconcileTimer = setTimeout(resolve, ms)
  })
}

async function reconcileLoop(version: number): Promise<void> {
  for (let i = 0; i < RECONCILE_MAX_ATTEMPTS; i++) {
    if (version !== _genVersion || !_active) return

    reconcileAttempt.value = i + 1

    if (import.meta.env.DEV) {
      console.log(`[plan-generate] reconciliation attempt ${i + 1}/${RECONCILE_MAX_ATTEMPTS}`)
    }

    const matchedPlan = await queryAndMatch()

    if (version !== _genVersion || !_active) return

    if (matchedPlan) {
      if (import.meta.env.DEV) {
        console.log('[plan-generate] matched generated plan, id:', matchedPlan.id)
      }
      generateStatus.value = 'success'
      clearLock()
      uni.showToast({ title: '计划生成成功！', icon: 'success' })
      uni.redirectTo({ url: `/pages/plan/detail?id=${matchedPlan.id}` })
      return
    }

    // 还有下一次尝试 → 等待
    if (i < RECONCILE_MAX_ATTEMPTS - 1) {
      await sleep(RECONCILE_INTERVAL_MS)
    }
  }

  // 确认耗尽
  if (version !== _genVersion || !_active) return

  if (import.meta.env.DEV) {
    console.log('[plan-generate] reconciliation exhausted')
  }
  generateStatus.value = 'uncertain'
  statusMessage.value = 'AI 生成耗时较长，暂时无法确认结果。计划可能仍在生成，请稍后前往"旅行计划"列表查看。'
  // uncertain 时保留锁，防止用户立即重复提交
}

// ==================== 计划匹配 ====================

async function queryAndMatch(): Promise<TravelPlan | null> {
  if (!ctx) return null

  try {
    const plans = await getMyPlans({ skip: 0, limit: 20 })
    if (!Array.isArray(plans) || plans.length === 0) return null

    // 候选：id 不在基线中 + 创建时间晚于提交时间 + destination/days 匹配
    const candidates = plans.filter(p => {
      if (!p || typeof p.id !== 'number') return false
      // 排除基线中已有的计划
      if (ctx!.baselinePlanIds.has(p.id)) return false
      // 创建时间校验
      if (!p.created_at) return false
      const createdTs = Date.parse(p.created_at)
      if (isNaN(createdTs) || createdTs < ctx!.submitTime - 5000) return false  // 允许 5 秒容差
      // destination 匹配（不区分大小写和首尾空格）
      const planDest = (p.destination || '').trim().toLowerCase()
      const ctxDest = ctx!.destination.trim().toLowerCase()
      if (planDest !== ctxDest) return false
      // days 匹配
      if (p.days !== ctx!.days) return false
      return true
    })

    if (candidates.length === 1) return candidates[0]

    // 多个候选时降低置信度——仅当基线无异常且只有一个候选时自动确认
    return null
  } catch {
    return null
  }
}

// ==================== 导航 ====================

function goToPlanList(): void {
  uni.navigateTo({ url: '/pages/plan/list' })
}

function handleRetryCheck(): void {
  if (!_active) return
  _genVersion++
  const version = _genVersion
  reconcileAttempt.value = 0
  generateStatus.value = 'confirming'
  statusMessage.value = '正在重新确认结果……'
  void reconcileLoop(version)
}

function handleForceRegenerate(): void {
  uni.showModal({
    title: '重新生成',
    content: '此前的生成请求可能仍在进行。重新生成可能导致重复计划，确定继续？',
    confirmText: '确定',
    cancelText: '取消',
    success(res) {
      if (res.confirm) {
        clearLock()
        void doGenerate()
      }
    },
  })
}

// ==================== 预填（从重新生成入口进入） ====================

onLoad((options: any) => {
  if (options?.from === 'regenerate') {
    if (options.destination) {
      destination.value = safeDecodeURIComponent(options.destination)
    }
    const d = parseIntegerInRange(options.days, 1, 10)
    if (d !== null) days.value = d
    if (options.budget !== undefined && options.budget !== null && String(options.budget) !== '') {
      const b = Number(options.budget)
      if (Number.isFinite(b) && b >= 0) budget.value = b
    }
    const t = parseIntegerInRange(options.travelers, 1, 20)
    if (t !== null) travelers.value = t
  }
})

// ==================== 生命周期清理 ====================

onUnload(() => {
  _active = false
  if (_reconcileTimer) {
    clearTimeout(_reconcileTimer)
    _reconcileTimer = null
  }
})

// ==================== 辅助函数 ====================

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
          :disabled="isBusy"
        />
      </view>

      <!-- 天数 -->
      <view class="form-group">
        <text class="form-label">天数 <text class="required">*</text></text>
        <view class="stepper-row">
          <button class="stepper-btn" :disabled="days <= 1 || isBusy" @tap="days--">-</button>
          <text class="stepper-value">{{ days }}</text>
          <button class="stepper-btn" :disabled="days >= 10 || isBusy" @tap="days++">+</button>
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
          :disabled="isBusy"
        />
      </view>

      <!-- 人数 -->
      <view class="form-group">
        <text class="form-label">出行人数</text>
        <view class="stepper-row">
          <button class="stepper-btn" :disabled="travelers <= 1 || isBusy" @tap="travelers--">-</button>
          <text class="stepper-value">{{ travelers }}</text>
          <button class="stepper-btn" :disabled="travelers >= 20 || isBusy" @tap="travelers++">+</button>
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
          :disabled="isBusy"
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
          :disabled="isBusy"
        />
        <text class="char-count">{{ notes.length }}/1000</text>
      </view>
    </scroll-view>

    <!-- 生成按钮 -->
    <view class="bottom-bar safe-area-bottom">
      <!-- 状态消息 -->
      <view v-if="statusMessage" class="status-msg" :class="{ 'status-uncertain': generateStatus === 'uncertain' }">
        <text>{{ statusMessage }}</text>
      </view>

      <!-- idle / failed: 显示普通生成按钮 -->
      <template v-if="generateStatus === 'idle' || generateStatus === 'failed'">
        <button
          class="generate-btn"
          :disabled="!destination.trim()"
          @tap="handleGenerate"
        >
          <text>开始生成</text>
        </button>
      </template>

      <!-- submitting / generating / confirming: 显示进度按钮（不可点击） -->
      <template v-else-if="generateStatus === 'submitting' || generateStatus === 'generating' || generateStatus === 'confirming'">
        <view class="generate-btn disabled">
          <text>{{ buttonText }}</text>
        </view>
      </template>

      <!-- uncertain: 显示操作入口 -->
      <template v-else-if="generateStatus === 'uncertain'">
        <view class="uncertain-actions">
          <view class="action-btn secondary" @tap="handleRetryCheck">
            <text>重新检查</text>
          </view>
          <view class="action-btn primary" @tap="goToPlanList">
            <text>前往计划列表</text>
          </view>
        </view>
        <view class="force-regenerate" @tap="handleForceRegenerate">
          <text>仍要重新生成</text>
        </view>
      </template>

      <!-- success: 跳转中，不显示按钮 -->
      <template v-else-if="generateStatus === 'success'">
        <view class="generate-btn disabled">
          <text>生成成功，正在跳转……</text>
        </view>
      </template>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.generate-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.form-scroll {
  flex: 1;
  padding: 24rpx 32rpx;
  width: 100%;
  box-sizing: border-box;
}

.form-group {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.form-label {
  font-size: 28rpx;
  color: #333;
  font-weight: 600;
  margin-bottom: 16rpx;
  display: block;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.required {
  color: #FF6B35;
}

.form-input {
  width: 100%;
  height: 72rpx;
  background: #f8f8f8;
  border-radius: 12rpx;
  padding: 0 20rpx;
  font-size: 28rpx;
  box-sizing: border-box;
  max-width: 100%;
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
  min-width: 0;
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
  flex-shrink: 0;
}

.stepper-btn[disabled] {
  opacity: 0.4;
}

.stepper-value {
  font-size: 32rpx;
  font-weight: 700;
  min-width: 60rpx;
  text-align: center;
  flex-shrink: 0;
}

.tag-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
  min-width: 0;
}

.pref-tag {
  padding: 12rpx 24rpx;
  border-radius: 32rpx;
  background: #f0f0f0;
  font-size: 26rpx;
  color: #666;
  border: 2rpx solid transparent;
  flex-shrink: 0;
}

.pref-tag.active {
  background: #e8f0fe;
  color: #4A90D9;
  border-color: #4A90D9;
}

.form-textarea {
  width: 100%;
  max-width: 100%;
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
  width: 100%;
  box-sizing: border-box;
}

.generate-btn {
  width: 100%;
  max-width: 100%;
  height: 88rpx;
  background: #4A90D9;
  color: #fff;
  font-size: 32rpx;
  border-radius: 44rpx;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  box-sizing: border-box;
  overflow-wrap: anywhere;
}

.generate-btn[disabled] {
  background: #ccc;
}

.generate-btn.disabled {
  background: #8ab4e0;
  color: #fff;
  font-size: 28rpx;
}

// Status message
.status-msg {
  padding: 16rpx 24rpx;
  margin-bottom: 16rpx;
  background: #e8f0fe;
  border-radius: 12rpx;
  font-size: 26rpx;
  color: #4A90D9;
  text-align: center;
  line-height: 1.5;
}

.status-msg.status-uncertain {
  background: #fff8e1;
  color: #e6a23c;
}

// Uncertain actions
.uncertain-actions {
  display: flex;
  gap: 20rpx;
  margin-bottom: 12rpx;
}

.action-btn {
  flex: 1;
  height: 80rpx;
  border-radius: 40rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
}

.action-btn.primary {
  background: #4A90D9;
  color: #fff;
}

.action-btn.secondary {
  background: #f5f5f5;
  color: #4A90D9;
  border: 1px solid #4A90D9;
}

.force-regenerate {
  text-align: center;
  padding: 12rpx 0;
  font-size: 24rpx;
  color: #bbb;
}
</style>
