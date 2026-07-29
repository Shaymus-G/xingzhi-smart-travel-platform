<script setup lang="ts">
/**
 * 通用收藏评论组件 — 支持五类可导航资源
 */
import { ref, computed, watch } from 'vue'
import type { SocialTargetType } from '@/types/resource'
import type { Review } from '@/types/social'
import { getFavorites, addFavorite, deleteFavorite, getReviews, createReview } from '@/api/social'
import { useUserStore } from '@/stores/user'
import ReviewItem from '@/components/ReviewItem.vue'

// ==================== Props ====================

interface Props {
  targetType: SocialTargetType
  targetId: number
  /** 水平内边距，默认 32rpx，通用资源详情页传 24rpx */
  horizontalPadding?: string
}

const props = withDefaults(defineProps<Props>(), {
  horizontalPadding: '32rpx',
})

// ==================== 认证 ====================

const userStore = useUserStore()
const isLoggedIn = computed(() => userStore.isLoggedIn)

// ==================== 请求版本 ====================

let targetVersion = 0

// ==================== 收藏状态 ====================

const favoriteId = ref<number | null>(null)
const favoriteStatusLoading = ref(false)
const favoriteActionLoading = ref(false)
const favoriteStatusError = ref<string | null>(null)

const isFavorited = computed(() => favoriteId.value !== null)

function isValid(): boolean {
  return typeof props.targetId === 'number' && Number.isInteger(props.targetId) && props.targetId > 0
}

async function loadFavoriteStatus(): Promise<void> {
  if (!isLoggedIn.value || !isValid()) return
  favoriteStatusLoading.value = true
  favoriteStatusError.value = null
  const version = targetVersion

  const MAX_PAGES = 10
  const PAGE_SIZE = 100

  try {
    for (let page = 0; page < MAX_PAGES; page++) {
      if (version !== targetVersion) return
      const favs = await getFavorites({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
      const found = favs.find(f => f.target_type === props.targetType && f.target_id === props.targetId)
      if (found) {
        if (version !== targetVersion) return
        favoriteId.value = found.id
        return
      }
      if (favs.length < PAGE_SIZE) break
    }
    if (version === targetVersion) favoriteId.value = null
  } catch (err: unknown) {
    if (version !== targetVersion) return
    favoriteStatusError.value = err instanceof Error ? err.message : '收藏状态查询失败'
  } finally {
    if (version === targetVersion) favoriteStatusLoading.value = false
  }
}

async function toggleFavorite(): Promise<void> {
  if (!isLoggedIn.value) { goLogin(); return }
  if (favoriteActionLoading.value || !isValid()) return
  favoriteActionLoading.value = true

  try {
    if (isFavorited.value && favoriteId.value) {
      await deleteFavorite(favoriteId.value)
      favoriteId.value = null
      uni.showToast({ title: '已取消收藏', icon: 'success' })
    } else {
      const fav = await addFavorite({ target_type: props.targetType, target_id: props.targetId })
      favoriteId.value = fav.id
      uni.showToast({ title: '已收藏', icon: 'success' })
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '操作失败'
    if (msg.includes('已收藏')) { void loadFavoriteStatus(); return }
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    favoriteActionLoading.value = false
  }
}

// ==================== 评论 ====================

const reviews = ref<Review[]>([])
const reviewsLoading = ref(false)
const reviewsError = ref<string | null>(null)

const reviewContent = ref('')
const reviewScore = ref(5)
const reviewSubmitting = ref(false)

async function loadReviews(): Promise<void> {
  if (!isValid()) return
  reviewsLoading.value = true
  reviewsError.value = null
  const version = targetVersion

  try {
    const list = await getReviews({ target_type: props.targetType, target_id: props.targetId, skip: 0, limit: 20 })
    if (version !== targetVersion) return
    reviews.value = list || []
  } catch (err: unknown) {
    if (version !== targetVersion) return
    reviewsError.value = err instanceof Error ? err.message : '评论加载失败'
  } finally {
    if (version === targetVersion) reviewsLoading.value = false
  }
}

async function submitReview(): Promise<void> {
  if (!isLoggedIn.value) { goLogin(); return }
  const content = reviewContent.value.trim()
  if (!content) { uni.showToast({ title: '请输入评论内容', icon: 'none' }); return }
  if (reviewScore.value < 1 || reviewScore.value > 5) { uni.showToast({ title: '评分需在 1-5 之间', icon: 'none' }); return }
  if (reviewSubmitting.value) return
  reviewSubmitting.value = true

  try {
    await createReview({ target_type: props.targetType, target_id: props.targetId, content, score: reviewScore.value })
    reviewContent.value = ''
    reviewScore.value = 5
    uni.showToast({ title: '评论成功', icon: 'success' })
    void loadReviews()
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '评论失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    reviewSubmitting.value = false
  }
}

// ==================== 登录 ====================

function goLogin(): void {
  uni.showToast({ title: '请先登录', icon: 'none' })
  uni.navigateTo({ url: '/pages/auth/login' })
}

// ==================== 生命周期 ====================

watch(
  () => [props.targetType, props.targetId, userStore.isLoggedIn] as const,
  () => {
    targetVersion++
    resetAndLoad()
  },
  { immediate: true },
)

function resetAndLoad(): void {
  favoriteId.value = null
  favoriteStatusError.value = null
  reviews.value = []
  reviewsError.value = null
  reviewContent.value = ''
  reviewScore.value = 5
  void Promise.all([loadFavoriteStatus(), loadReviews()])
}
</script>

<template>
  <view v-if="isValid()" class="rss-container" :style="{ paddingLeft: horizontalPadding, paddingRight: horizontalPadding }">
    <!-- 收藏区 -->
    <view class="rss-favorite-bar">
      <view
        class="rss-fav-btn"
        :class="{ active: isFavorited, loading: favoriteActionLoading }"
        @tap="toggleFavorite"
      >
        <text>{{ favoriteActionLoading ? '...' : isFavorited ? '❤️ 已收藏' : '🤍 收藏' }}</text>
      </view>
      <text v-if="!isLoggedIn" class="rss-login-hint" @tap="goLogin">登录后收藏</text>
    </view>

    <!-- 评论区 -->
    <view class="rss-reviews">
      <text class="rss-section-title">评论 ({{ reviews.length }})</text>

      <!-- 评论加载 -->
      <view v-if="reviewsLoading" class="rss-status"><text>加载评论...</text></view>

      <!-- 评论错误 -->
      <view v-else-if="reviewsError" class="rss-status rss-error">
        <text>{{ reviewsError }}</text>
        <view class="rss-retry" @tap="loadReviews()"><text>重试</text></view>
      </view>

      <!-- 评论列表 -->
      <template v-else-if="reviews.length > 0">
        <ReviewItem v-for="r in reviews" :key="r.id" :review="r" />
      </template>

      <!-- 评论空 -->
      <view v-else class="rss-status"><text>暂无评论</text></view>

      <!-- 评论表单 -->
      <view v-if="isLoggedIn" class="rss-form">
        <view class="rss-score-row">
          <text class="rss-score-label">评分</text>
          <view class="rss-stars">
            <text
              v-for="s in 5" :key="s"
              class="rss-star"
              :class="{ active: s <= reviewScore }"
              @tap="reviewScore = s"
            >★</text>
          </view>
        </view>
        <textarea
          v-model="reviewContent"
          class="rss-textarea"
          placeholder="写下你的评论..."
          :maxlength="500"
          :disabled="reviewSubmitting"
        />
        <view
          class="rss-submit"
          :class="{ disabled: reviewSubmitting || !reviewContent.trim() }"
          @tap="submitReview"
        >
          <text>{{ reviewSubmitting ? '提交中...' : '发表评论' }}</text>
        </view>
      </view>

      <!-- 未登录评论入口 -->
      <view v-else class="rss-form rss-login-form">
        <text class="rss-login-hint" @tap="goLogin">登录后发表评论</text>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.rss-container {
  background: #fff;
  margin: 20rpx 0;
  box-sizing: border-box;
  width: 100%;
}

// Favorite
.rss-favorite-bar {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 24rpx 0;
  border-bottom: 1rpx solid #f0f0f0;
}

.rss-fav-btn {
  padding: 12rpx 28rpx;
  border: 1px solid #e0e0e0;
  border-radius: 32rpx;
  font-size: 26rpx;
  color: #666;
}

.rss-fav-btn.active {
  color: #FF6B35;
  border-color: #FF6B35;
  background: rgba(255,107,53,0.05);
}

.rss-fav-btn.loading {
  opacity: 0.5;
}

.rss-login-hint {
  font-size: 24rpx;
  color: #4A90D9;
}

// Reviews
.rss-reviews {
  padding: 24rpx 0;
}

.rss-section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 16rpx;
}

.rss-status {
  padding: 32rpx 0;
  text-align: center;
  font-size: 26rpx;
  color: #999;
}

.rss-error {
  color: #d93025;
}

.rss-retry {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #4A90D9;
}

// Form
.rss-form {
  margin-top: 24rpx;
  padding-top: 24rpx;
  border-top: 1rpx solid #f0f0f0;
}

.rss-score-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 16rpx;
}

.rss-score-label {
  font-size: 26rpx;
  color: #666;
}

.rss-stars {
  display: flex;
  gap: 8rpx;
}

.rss-star {
  font-size: 36rpx;
  color: #ddd;
}

.rss-star.active {
  color: #FF8C00;
}

.rss-textarea {
  width: 100%;
  min-height: 120rpx;
  background: #f8f8f8;
  border-radius: 12rpx;
  padding: 16rpx;
  font-size: 26rpx;
  box-sizing: border-box;
  margin-bottom: 16rpx;
}

.rss-submit {
  padding: 16rpx 0;
  background: #4A90D9;
  border-radius: 12rpx;
  text-align: center;
  font-size: 28rpx;
  color: #fff;
}

.rss-submit.disabled {
  background: #ccc;
}

.rss-login-form {
  text-align: center;
}
</style>
