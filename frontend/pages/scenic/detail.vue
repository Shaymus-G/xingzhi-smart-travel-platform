<script setup lang="ts">
/**
 * 景点详情页 — 信息展示 + 收藏 + 评论
 */
import { ref, computed } from 'vue'
import { onLoad, onShow, onReady } from '@dcloudio/uni-app'
import NavBar from '@/components/NavBar.vue'
import EmptyState from '@/components/EmptyState.vue'
import Loading from '@/components/Loading.vue'
import ReviewItem from '@/components/ReviewItem.vue'
import { getScenicDetail } from '@/api/travel'
import { getFavorites, addFavorite, deleteFavorite } from '@/api/social'
import { getReviews, createReview } from '@/api/social'
import { useUserStore } from '@/stores/user'
import type { ScenicSpot } from '@/types/travel'
import type { Review } from '@/types/social'

const userStore = useUserStore()

// ========== 路由 ==========
const scenicId = ref(0)

// ========== 景点数据 ==========
const scenic = ref<ScenicSpot | null>(null)
const loading = ref(false)

// ========== 收藏 ==========
const isFavorited = ref(false)
const currentFavoriteId = ref<number | null>(null)
const favoriteLoading = ref(false)

// ========== 评论 ==========
const reviews = ref<Review[]>([])
const reviewsLoading = ref(false)

// ========== 发表评论 ==========
const reviewContent = ref('')
const reviewScore = ref(5)
const reviewSubmitting = ref(false)

// ========== 图片 ==========
const FALLBACK = '/static/logo.png'

// ========== tags 解析 ==========
const parsedTags = computed<string[]>(() => {
  const raw = scenic.value?.tags_json
  if (!raw) return []
  if (Array.isArray(raw)) return raw.map(String)
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

function fmt(val?: number | string | null, prefix = '', suffix = ''): string {
  if (val === null || val === undefined || val === '') return ''
  const n = Number(val)
  return isNaN(n) ? '' : `${prefix}${n}${suffix}`
}

// ========== 加载景点 ==========
async function loadScenic() {
  if (!scenicId.value) return
  loading.value = true
  try {
    scenic.value = await getScenicDetail(scenicId.value)
  } catch (err) {
    const msg = err instanceof Error ? err.message : '加载失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    loading.value = false
  }
}

// ========== 收藏逻辑 ==========
async function loadFavoriteStatus() {
  if (!userStore.isLoggedIn) return
  try {
    const favs = await getFavorites()
    const found = favs.find(
      f => f.target_type === 'scenic_spot' && f.target_id === scenicId.value
    )
    if (found) {
      isFavorited.value = true
      currentFavoriteId.value = found.id
    } else {
      isFavorited.value = false
      currentFavoriteId.value = null
    }
  } catch {
    // 静默失败，不影响页面展示
  }
}

async function toggleFavorite() {
  if (!userStore.isLoggedIn) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    uni.navigateTo({ url: '/pages/auth/login' })
    return
  }

  favoriteLoading.value = true
  try {
    if (isFavorited.value && currentFavoriteId.value) {
      await deleteFavorite(currentFavoriteId.value)
      isFavorited.value = false
      currentFavoriteId.value = null
      uni.showToast({ title: '已取消收藏', icon: 'success' })
    } else {
      const fav = await addFavorite({
        target_type: 'scenic_spot',
        target_id: scenicId.value,
      })
      isFavorited.value = true
      currentFavoriteId.value = fav.id
      uni.showToast({ title: '收藏成功', icon: 'success' })
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : '操作失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    favoriteLoading.value = false
  }
}

// ========== 评论逻辑 ==========
async function loadReviews() {
  reviewsLoading.value = true
  try {
    const data = await getReviews({
      target_type: 'scenic_spot',
      target_id: scenicId.value,
    })
    reviews.value = data || []
  } catch {
    // 静默失败
  } finally {
    reviewsLoading.value = false
  }
}

function goLogin() {
  uni.navigateTo({ url: '/pages/auth/login' })
}

async function submitReview() {
  const content = reviewContent.value.trim()
  if (!content) {
    uni.showToast({ title: '请输入评论内容', icon: 'none' })
    return
  }
  if (reviewScore.value < 1 || reviewScore.value > 5) {
    uni.showToast({ title: '评分需在1-5之间', icon: 'none' })
    return
  }

  reviewSubmitting.value = true
  try {
    const newReview = await createReview({
      target_type: 'scenic_spot',
      target_id: scenicId.value,
      content,
      score: reviewScore.value,
    })
    // 插入到列表顶部
    reviews.value.unshift(newReview)
    reviewContent.value = ''
    reviewScore.value = 5
    uni.showToast({ title: '评论成功', icon: 'success' })
  } catch (err) {
    const msg = err instanceof Error ? err.message : '评论失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    reviewSubmitting.value = false
  }
}

// ========== 生命周期 ==========
onLoad((options: any) => {
  console.log('[scenic/detail] onLoad options:', JSON.stringify(options))
  const id = Number(options?.id)
  if (!id || isNaN(id)) {
    uni.showToast({ title: '景点ID无效', icon: 'none' })
    uni.navigateBack()
    return
  }
  scenicId.value = id
  Promise.all([loadScenic(), loadReviews()]).then(() => {
    loadFavoriteStatus()
  })
})

onShow(() => {
  console.log('[scenic/detail] onShow, scenicId:', scenicId.value)
})

onReady(() => {
  console.log('[scenic/detail] onReady')
})
</script>

<template>
  <view class="scenic-detail-page">
    <NavBar title="景点详情" :show-back="true" />
    <view class="debug-title">景点详情页 id={{ scenicId }}</view>

    <scroll-view class="scenic-scroll" scroll-y enhanced :show-scrollbar="false">
      <Loading :visible="loading" />

      <template v-if="!loading && scenic">
        <!-- 封面图 -->
        <image class="scenic-cover" :src="scenic.image_url || FALLBACK" mode="aspectFill" />

        <!-- 基本信息 -->
        <view class="scenic-info">
          <view class="scenic-header">
            <text class="scenic-name">{{ scenic.name }}</text>
            <view class="scenic-favorite" @tap="toggleFavorite">
              <text v-if="favoriteLoading">⏳</text>
              <text v-else>{{ isFavorited ? '❤️' : '🤍' }}</text>
            </view>
          </view>

          <view v-if="parsedTags.length > 0" class="scenic-tags">
            <text v-for="tag in parsedTags" :key="tag" class="scenic-tag">{{ tag }}</text>
          </view>

          <view class="scenic-meta">
            <text v-if="fmt(scenic.score)" class="scenic-meta-item">★ {{ fmt(scenic.score) }}</text>
            <text v-if="fmt(scenic.price, '¥')" class="scenic-meta-item">¥{{ fmt(scenic.price) }}</text>
            <text v-if="scenic.category" class="scenic-meta-item">{{ scenic.category }}</text>
            <text v-if="scenic.open_time" class="scenic-meta-item">{{ scenic.open_time }}</text>
          </view>

          <text v-if="scenic.address" class="scenic-address">📍 {{ scenic.address }}</text>
          <text v-if="scenic.description" class="scenic-desc">{{ scenic.description }}</text>
        </view>

        <!-- 评论区域 -->
        <view class="scenic-section">
          <text class="scenic-section-title">游客评论 ({{ reviews.length }})</text>

          <Loading :visible="reviewsLoading" text="加载评论..." />

          <template v-if="!reviewsLoading">
            <EmptyState
              v-if="reviews.length === 0"
              text="暂无评论"
              sub-text="来发表第一条评论吧"
            />

            <ReviewItem
              v-for="review in reviews"
              :key="review.id"
              :review="review"
            />
          </template>
        </view>

        <!-- 发表评论 -->
        <view class="scenic-section">
          <text class="scenic-section-title">发表评论</text>

          <template v-if="userStore.isLoggedIn">
            <view class="review-editor">
              <view class="review-editor-score">
                <text class="review-editor-label">评分</text>
                <view class="review-editor-stars">
                  <text
                    v-for="s in 5"
                    :key="s"
                    class="review-editor-star"
                    :class="{ active: s <= reviewScore }"
                    @tap="reviewScore = s"
                  >
                    {{ s <= reviewScore ? '★' : '☆' }}
                  </text>
                </view>
              </view>

              <textarea
                v-model="reviewContent"
                class="review-editor-textarea"
                placeholder="写下你的感受吧..."
                placeholder-style="color: #ccc;"
                :maxlength="500"
              />

              <button
                class="review-editor-btn"
                :loading="reviewSubmitting"
                :disabled="reviewSubmitting || !reviewContent.trim()"
                @tap="submitReview"
              >
                提交评论
              </button>
            </view>
          </template>

          <template v-else>
            <view class="review-login-tip">
              <text class="review-login-text">登录后发表评论</text>
              <button class="review-login-btn" @tap="goLogin">去登录</button>
            </view>
          </template>
        </view>
      </template>

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
.debug-title {
  background: #FF6B35;
  color: #fff;
  font-size: 24rpx;
  padding: 8rpx 24rpx;
  text-align: center;
}

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

// ========== 评论编辑器 ==========
.review-editor {
  margin-top: 16rpx;
}

.review-editor-score {
  display: flex;
  align-items: center;
  margin-bottom: 16rpx;
}

.review-editor-label {
  font-size: 28rpx;
  color: #333;
  margin-right: 16rpx;
}

.review-editor-stars {
  display: flex;
  gap: 8rpx;
}

.review-editor-star {
  font-size: 40rpx;
  color: #ddd;
}

.review-editor-star.active {
  color: #FF8C00;
}

.review-editor-textarea {
  width: 100%;
  height: 180rpx;
  background: #f7f8fa;
  border-radius: 12rpx;
  padding: 16rpx 20rpx;
  font-size: 28rpx;
  box-sizing: border-box;
  margin-bottom: 16rpx;
}

.review-editor-btn {
  height: 80rpx;
  background: #4A90D9;
  color: #fff;
  font-size: 28rpx;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.review-editor-btn[disabled] {
  opacity: 0.7;
}

// ========== 未登录提示 ==========
.review-login-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40rpx 0;
}

.review-login-text {
  font-size: 28rpx;
  color: #999;
  margin-bottom: 20rpx;
}

.review-login-btn {
  background: #4A90D9;
  color: #fff;
  font-size: 28rpx;
  padding: 12rpx 48rpx;
  border-radius: 32rpx;
}
</style>
