<script setup lang="ts">
/**
 * 实时路线查询与展示组件 — 固定起点→终点
 */
import { ref } from 'vue'
import { getTransitRoute } from '@/api/transit'
import { isNavigableResourceType } from '@/types/resource'
import type { TransitEndpointType, TransitMethod, TransitRouteResult, TransitSegment, TransitStep } from '@/types/transit'

// ==================== Props ====================

interface Props {
  originType: TransitEndpointType
  originId: number
  originName: string
  destinationType: TransitEndpointType
  destinationId: number
  destinationName: string
  city?: string
}

const props = defineProps<Props>()

// ==================== 方式配置 ====================

interface MethodOption {
  value: TransitMethod
  label: string
}

const methodOptions: MethodOption[] = [
  { value: 'transit', label: '公交' },
  { value: 'driving', label: '驾车' },
  { value: 'walking', label: '步行' },
  { value: 'bicycling', label: '骑行' },
]

// ==================== 状态 ====================

const selectedMethod = ref<TransitMethod>('transit')
const currentResult = ref<TransitRouteResult | null>(null)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)

const routeCache = new Map<string, TransitRouteResult>()
let requestVersion = 0

// ==================== Props 校验 ====================

function isValid(): boolean {
  if (typeof props.originId !== 'number' || !Number.isInteger(props.originId) || props.originId <= 0) return false
  if (typeof props.destinationId !== 'number' || !Number.isInteger(props.destinationId) || props.destinationId <= 0) return false
  if (!isNavigableResourceType(props.originType)) return false
  if (!isNavigableResourceType(props.destinationType)) return false
  if (props.originType === props.destinationType && props.originId === props.destinationId) return false
  return true
}

// ==================== 缓存 ====================

function cacheKey(method: TransitMethod): string {
  return `${props.originType}:${props.originId}|${props.destinationType}:${props.destinationId}|${method}|${props.city ?? ''}`
}

// ==================== 查询 ====================

async function queryRoute(): Promise<void> {
  if (!isValid()) return

  // 公交缺city
  if (selectedMethod.value === 'transit' && (!props.city || !props.city.trim())) {
    errorMessage.value = '公交路线需要城市信息'
    currentResult.value = null
    return
  }

  const key = cacheKey(selectedMethod.value)
  const cached = routeCache.get(key)
  if (cached) {
    currentResult.value = cached
    errorMessage.value = null
    return
  }

  if (isLoading.value) return
  isLoading.value = true
  errorMessage.value = null
  const version = ++requestVersion

  try {
    const result = await getTransitRoute({
      from_type: props.originType,
      from_id: props.originId,
      to_type: props.destinationType,
      to_id: props.destinationId,
      method: selectedMethod.value,
      city: props.city?.trim() || undefined,
    })

    if (version !== requestVersion) return
    routeCache.set(key, result)
    currentResult.value = result
  } catch (err: unknown) {
    if (version !== requestVersion) return
    errorMessage.value = classifyError(err)
    currentResult.value = null
  } finally {
    if (version === requestVersion) isLoading.value = false
  }
}

// ==================== 方式切换 ====================

function onMethodChange(method: TransitMethod): void {
  selectedMethod.value = method
  requestVersion++

  const key = cacheKey(method)
  const cached = routeCache.get(key)
  if (cached) {
    currentResult.value = cached
    errorMessage.value = null
  } else {
    currentResult.value = null
    errorMessage.value = null
  }
}

// ==================== 错误分类 ====================

function classifyError(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err ?? '')
  if (msg.includes('未找到') || msg.includes('不存在')) return '路线端点不存在'
  if (msg.includes('缺少坐标') || msg.includes('坐标')) return '该资源缺少坐标信息'
  if (msg.includes('暂无') || msg.includes('没有')) return '暂无可用路线，可尝试其他方式'
  if (msg.includes('路径规划失败') || msg.includes('服务')) return '路线服务暂不可用'
  if (msg.includes('网络') || msg.includes('超时') || msg.includes('fail')) return '网络请求失败，请稍后重试'
  return msg || '路线查询失败'
}

// ==================== 格式化 ====================

function fmtVal(value: string | number | null | undefined): string | null {
  if (value === null || value === undefined) return null
  if (typeof value === 'string') {
    const t = value.trim()
    return t || null
  }
  return Number.isFinite(value) ? String(value) : null
}

function segmentLabel(seg: TransitSegment): string {
  if (seg.type === 'walking') return '步行'
  if (seg.type === 'subway') return '地铁'
  if (seg.type === 'bus') return '公交'
  return seg.type || '换乘'
}
</script>

<template>
  <view v-if="isValid()" class="trp-container">
    <view class="trp-header">
      <text class="trp-title">实时路线</text>
      <text class="trp-endpoints">{{ originName }} → {{ destinationName }}</text>
    </view>

    <!-- 方式选择 -->
    <view class="trp-methods">
      <text
        v-for="m in methodOptions"
        :key="m.value"
        class="trp-method"
        :class="{ active: selectedMethod === m.value }"
        @tap="onMethodChange(m.value)"
      >{{ m.label }}</text>
    </view>

    <!-- 查询按钮 -->
    <view class="trp-query-btn" :class="{ loading: isLoading }" @tap="queryRoute">
      <text>{{ isLoading ? '查询中...' : '查询路线' }}</text>
    </view>

    <!-- 错误 -->
    <view v-if="errorMessage" class="trp-error">
      <text>{{ errorMessage }}</text>
      <text v-if="errorMessage.includes('网络') || errorMessage.includes('服务')" class="trp-retry" @tap="queryRoute">重试</text>
    </view>

    <!-- 结果 -->
    <view v-if="currentResult" class="trp-result">
      <text class="trp-summary">{{ currentResult.distance }} · {{ currentResult.duration }}</text>

      <view v-if="currentResult.method === 'transit'">
        <text v-if="fmtVal(currentResult.cost)" class="trp-meta">💰 {{ fmtVal(currentResult.cost) }}</text>
        <text v-if="fmtVal(currentResult.walking_distance)" class="trp-meta">🚶 步行 {{ fmtVal(currentResult.walking_distance) }}</text>

        <view v-if="currentResult.segments.length > 0" class="trp-steps">
          <view v-for="(seg, si) in currentResult.segments" :key="si" class="trp-step">
            <text class="trp-step-type">{{ segmentLabel(seg) }}</text>
            <view class="trp-step-body">
              <text v-if="seg.name" class="trp-step-name">{{ seg.name }}</text>
              <text v-if="seg.departure && seg.arrival" class="trp-step-stops">{{ seg.departure }} → {{ seg.arrival }}</text>
              <text v-if="seg.instruction" class="trp-step-desc">{{ seg.instruction }}</text>
            </view>
          </view>
        </view>
        <text v-else class="trp-no-steps">暂无详细步骤</text>
      </view>

      <view v-else>
        <text v-if="currentResult.method === 'driving' && fmtVal(currentResult.toll)" class="trp-meta">🛣️ 过路费 {{ fmtVal(currentResult.toll) }}</text>
        <text v-if="currentResult.method === 'driving' && currentResult.traffic_lights != null" class="trp-meta">🚦 {{ currentResult.traffic_lights }} 个红绿灯</text>

        <view v-if="currentResult.steps.length > 0" class="trp-steps">
          <view v-for="(step, si) in currentResult.steps" :key="si" class="trp-step">
            <text class="trp-step-desc">{{ step.instruction }}</text>
            <text v-if="fmtVal(step.distance)" class="trp-step-dist">{{ fmtVal(step.distance) }}</text>
          </view>
        </view>
        <text v-else class="trp-no-steps">暂无详细步骤</text>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.trp-container {
  background: #fafafa;
  border-radius: 12rpx;
  padding: 20rpx 24rpx;
  margin-top: 16rpx;
  border: 1rpx solid #eee;
}

.trp-header {
  margin-bottom: 12rpx;
}

.trp-title {
  font-size: 26rpx;
  font-weight: 600;
  color: #333;
  margin-right: 12rpx;
}

.trp-endpoints {
  font-size: 24rpx;
  color: #999;
}

.trp-methods {
  display: flex;
  gap: 12rpx;
  margin-bottom: 12rpx;
}

.trp-method {
  padding: 6rpx 18rpx;
  border-radius: 20rpx;
  font-size: 22rpx;
  color: #666;
  background: #f0f0f0;
}

.trp-method.active {
  background: #4A90D9;
  color: #fff;
}

.trp-query-btn {
  padding: 12rpx 0;
  background: #4A90D9;
  border-radius: 8rpx;
  text-align: center;
  font-size: 24rpx;
  color: #fff;
  margin-bottom: 12rpx;
}

.trp-query-btn.loading {
  opacity: 0.6;
}

.trp-error {
  padding: 12rpx 0;
  font-size: 24rpx;
  color: #d93025;
  text-align: center;
}

.trp-retry {
  margin-left: 8rpx;
  color: #4A90D9;
}

.trp-result {
  padding-top: 8rpx;
}

.trp-summary {
  font-size: 26rpx;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 8rpx;
}

.trp-meta {
  font-size: 24rpx;
  color: #666;
  display: block;
  margin-bottom: 4rpx;
}

.trp-steps {
  margin-top: 8rpx;
}

.trp-step {
  display: flex;
  gap: 12rpx;
  padding: 8rpx 0;
  border-top: 1rpx solid #eee;
}

.trp-step-type {
  font-size: 22rpx;
  color: #4A90D9;
  min-width: 50rpx;
}

.trp-step-body {
  flex: 1;
}

.trp-step-name {
  font-size: 24rpx;
  font-weight: 600;
  color: #333;
  display: block;
}

.trp-step-stops {
  font-size: 22rpx;
  color: #666;
  display: block;
}

.trp-step-desc {
  font-size: 24rpx;
  color: #666;
  display: block;
}

.trp-step-dist {
  font-size: 22rpx;
  color: #999;
}

.trp-no-steps {
  font-size: 24rpx;
  color: #999;
  padding: 8rpx 0;
}
</style>
