<script setup lang="ts">
/**
 * 我的收藏 — 展示五类资源收藏
 */
import { ref, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'
import EmptyState from '@/components/EmptyState.vue'
import { getFavorites, deleteFavorite } from '@/api/social'
import { openResourceDetail } from '@/utils/navigation'
import { getResourceTypeLabel } from '@/types/resource'
import type { SocialTargetType } from '@/types/resource'
import type { Favorite } from '@/types/social'

// ========== 状态 ==========
const loading = ref(false)
const error = ref<string | null>(null)
const favorites = ref<Favorite[]>([])
const deletingIds = ref<Set<number>>(new Set())

// ========== 加载 ==========

onMounted(() => { void loadFavorites() })

async function loadFavorites(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    favorites.value = await getFavorites({ skip: 0, limit: 100 }) || []
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

// ========== 删除 ==========

async function handleDelete(fav: Favorite): Promise<void> {
  if (deletingIds.value.has(fav.id)) return
  const modalRes = await uni.showModal({ title: '取消收藏', content: '确定取消收藏？', confirmText: '确定', confirmColor: '#d93025' })
  if (!modalRes.confirm) return

  const s = new Set(deletingIds.value); s.add(fav.id); deletingIds.value = s
  try {
    await deleteFavorite(fav.id)
    favorites.value = favorites.value.filter(f => f.id !== fav.id)
  } catch (err: unknown) {
    uni.showToast({ title: err instanceof Error ? err.message : '取消失败', icon: 'none' })
  } finally {
    const s2 = new Set(deletingIds.value); s2.delete(fav.id); deletingIds.value = s2
  }
}

// ========== 导航 ==========

function canNavigate(fav: Favorite): boolean {
  return typeof fav.target_type === 'string' && typeof fav.target_id === 'number' && fav.target_id > 0
}

function goDetail(fav: Favorite): void {
  if (canNavigate(fav)) {
    openResourceDetail(fav.target_type as SocialTargetType, fav.target_id)
  }
}

function formatDate(d: string | undefined): string {
  return d ? d.slice(0, 10) : ''
}
</script>

<template>
  <view class="favorites-page">
    <NavBar title="我的收藏" :show-back="true" />

    <view v-if="loading" class="fav-status"><text>加载中...</text></view>

    <view v-else-if="error" class="fav-status fav-error">
      <text>{{ error }}</text>
      <view class="fav-retry" @tap="loadFavorites()"><text>重试</text></view>
    </view>

    <EmptyState v-else-if="favorites.length === 0" text="暂无收藏" />

    <scroll-view v-else class="fav-list" scroll-y>
      <view
        v-for="fav in favorites"
        :key="fav.id"
        class="fav-card"
        @tap="goDetail(fav)"
      >
        <view class="fav-card-body">
          <view class="fav-card-header">
            <text class="fav-type-tag">{{ getResourceTypeLabel(fav.target_type as SocialTargetType, fav.target_type) }}</text>
            <text class="fav-id">#{{ fav.target_id }}</text>
          </view>
          <text class="fav-date">{{ formatDate(fav.created_at) }}</text>
        </view>
        <view
          class="fav-delete"
          :class="{ deleting: deletingIds.has(fav.id) }"
          @tap.stop="handleDelete(fav)"
        >
          <text>{{ deletingIds.has(fav.id) ? '...' : '取消' }}</text>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<style lang="scss" scoped>
.favorites-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.fav-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
  font-size: 28rpx;
  color: #999;
}

.fav-error {
  color: #d93025;
}

.fav-retry {
  margin-top: 16rpx;
  padding: 10rpx 36rpx;
  border: 1px solid #4A90D9;
  border-radius: 24rpx;
  font-size: 26rpx;
  color: #4A90D9;
}

.fav-list {
  padding: 16rpx 32rpx;
}

.fav-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.fav-card-body {
  flex: 1;
}

.fav-card-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 8rpx;
}

.fav-type-tag {
  padding: 4rpx 14rpx;
  background: #e8f0fe;
  color: #4A90D9;
  border-radius: 8rpx;
  font-size: 24rpx;
}

.fav-id {
  font-size: 24rpx;
  color: #bbb;
}

.fav-date {
  font-size: 24rpx;
  color: #bbb;
}

.fav-delete {
  padding: 8rpx 20rpx;
  border: 1px solid #d93025;
  border-radius: 24rpx;
  font-size: 22rpx;
  color: #d93025;
}

.fav-delete.deleting {
  opacity: 0.5;
  border-color: #ccc;
  color: #ccc;
}
</style>
