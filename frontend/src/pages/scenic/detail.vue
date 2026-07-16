<script setup lang="ts">
/**
 * 景点详情页
 */
import { ref, computed, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'
import EmptyState from '@/components/EmptyState.vue'
import Loading from '@/components/Loading.vue'
import { getScenicDetail } from '@/api/travel'
import type { ScenicSpot } from '@/types/travel'

// ========== 路由参数 ==========
const scenicId = ref(0)

// ========== 数据 ==========
const scenic = ref<ScenicSpot | null>(null)
const loading = ref(false)

// ========== 图片兜底 ==========
const FALLBACK = '/static/logo.png'

// ========== tags_json 兼容解析 ==========
const parsedTags = computed<string[]>(() => {
  const raw = scenic.value?.tags_json
  if (!raw) return []
  // 如果已经是数组
  if (Array.isArray(raw)) return raw.map(String)
  // 如果是 JSON 字符串
  if (typeof raw === 'string') {
    try {
      const arr = JSON.parse(raw)
      return Array.isArray(arr) ? arr.map(String) : []
    } catch {
      return [raw]
    }
  }
  return []
})

// ========== 格式化函数 ==========
function fmt(val?: number | string | null, prefix = '', suffix = ''): string {
  if (val === null || val === undefined || val === '') return ''
  const n = Number(val)
  return isNaN(n) ? '' : `${prefix}${n}${suffix}`
}

// ========== 方法 ==========

async function loadScenic() {
  if (!scenicId.value) return
  loading.value = true
  try {
    const data = await getScenicDetail(scenicId.value)
    scenic.value = data
  } catch (err) {
    const msg = err instanceof Error ? err.message : '加载失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    loading.value = false
  }
}

function onFavorite() {
  uni.showToast({ title: '收藏功能下一阶段实现', icon: 'none' })
}

// ========== 生命周期 ==========
onMounted(() => {
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as Record<string, unknown>
  const options = (currentPage?.options || {}) as Record<string, string>
  const id = Number(options?.id)
  if (!id || isNaN(id)) {
    uni.showToast({ title: '景点ID无效', icon: 'none' })
    uni.navigateBack()
    return
  }
  scenicId.value = id
  loadScenic()
})
</script>

<template>
  <view class="scenic-detail-page">
    <NavBar title="景点详情" :show-back="true" />

    <scroll-view class="scenic-scroll" scroll-y enhanced :show-scrollbar="false">
      <Loading :visible="loading" />

      <template v-if="!loading && scenic">
        <!-- 封面图 -->
        <image
          class="scenic-cover"
          :src="scenic.image_url || FALLBACK"
          mode="aspectFill"
        />

        <!-- 基本信息 -->
        <view class="scenic-info">
          <view class="scenic-header">
            <text class="scenic-name">{{ scenic.name }}</text>
            <view class="scenic-favorite" @tap="onFavorite">🤍</view>
          </view>

          <!-- 标签 -->
          <view v-if="parsedTags.length > 0" class="scenic-tags">
            <text v-for="tag in parsedTags" :key="tag" class="scenic-tag">{{ tag }}</text>
          </view>

          <!-- Meta -->
          <view class="scenic-meta">
            <text v-if="fmt(scenic.score)" class="scenic-meta-item">★ {{ fmt(scenic.score) }}</text>
            <text v-if="fmt(scenic.price, '¥')" class="scenic-meta-item">¥{{ fmt(scenic.price) }}</text>
            <text v-if="scenic.category" class="scenic-meta-item">{{ scenic.category }}</text>
            <text v-if="scenic.open_time" class="scenic-meta-item">{{ scenic.open_time }}</text>
          </view>

          <!-- 地址 -->
          <text v-if="scenic.address" class="scenic-address">📍 {{ scenic.address }}</text>

          <!-- 描述 -->
          <text v-if="scenic.description" class="scenic-desc">{{ scenic.description }}</text>
        </view>

        <!-- 评论占位 -->
        <view class="scenic-section">
          <text class="scenic-section-title">游客评论</text>
          <EmptyState
            text="评论功能下一阶段实现"
            sub-text="届时可查看和发表评论"
          />
        </view>
      </template>

      <!-- 加载失败 -->
      <EmptyState
        v-if="!loading && !scenic"
        text="加载失败"
        sub-text="请确认后端服务已启动"
      />

      <view style="height: 40rpx;" />
    </scroll-view>
  </view>
</template>

<style lang="scss" scoped>
.scenic-detail-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.scenic-scroll {
  flex: 1;
}

.scenic-cover {
  width: 100%;
  height: 420rpx;
  background: #e0e0e0;
}

.scenic-info {
  background: #fff;
  padding: 24rpx 32rpx;
}

.scenic-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.scenic-name {
  font-size: 38rpx;
  font-weight: 700;
  color: #333;
}

.scenic-favorite {
  font-size: 48rpx;
}

.scenic-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin: 16rpx 0 8rpx;
}

.scenic-tag {
  font-size: 24rpx;
  color: #4A90D9;
  background: rgba(74, 144, 217, 0.1);
  padding: 4rpx 14rpx;
  border-radius: 6rpx;
}

.scenic-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 24rpx;
  margin: 12rpx 0;
}

.scenic-meta-item {
  font-size: 26rpx;
  color: #666;
}

.scenic-address {
  font-size: 26rpx;
  color: #999;
  display: block;
  margin-bottom: 12rpx;
}

.scenic-desc {
  font-size: 28rpx;
  color: #666;
  line-height: 1.8;
}

.scenic-section {
  margin-top: 16rpx;
  background: #fff;
  padding: 24rpx 32rpx;
}

.scenic-section-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 8rpx;
}
</style>
