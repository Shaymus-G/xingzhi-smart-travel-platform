<script setup lang="ts">
/**
 * 我的收藏 — 展示已收藏的景点
 */
import { ref, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'
import ScenicCard from '@/components/ScenicCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import Loading from '@/components/Loading.vue'
import { getFavorites } from '@/api/social'
import { getScenicDetail } from '@/api/travel'
import { useUserStore } from '@/stores/user'
import type { Favorite } from '@/types/social'
import type { ScenicSpot } from '@/types/travel'

const userStore = useUserStore()
const loading = ref(false)
const scenicFavorites = ref<Array<{ favorite: Favorite; scenic: ScenicSpot | null }>>([])

async function loadFavorites() {
  loading.value = true
  try {
    const favs = await getFavorites()
    // 只处理 scenic_spot 收藏
    const scenicFavs = favs.filter(f => f.target_type === 'scenic_spot')

    // 并行获取每个收藏的景点详情
    const items = await Promise.all(
      scenicFavs.map(async (fav) => {
        try {
          const scenic = await getScenicDetail(fav.target_id)
          return { favorite: fav, scenic }
        } catch {
          return { favorite: fav, scenic: null }
        }
      })
    )
    scenicFavorites.value = items
  } catch (err) {
    const msg = err instanceof Error ? err.message : '加载失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    loading.value = false
  }
}

function goScenicDetail(id: number) {
  uni.navigateTo({ url: `/pages/scenic/detail?id=${id}` })
}

function goLogin() {
  uni.navigateTo({ url: '/pages/auth/login' })
}

onMounted(() => {
  if (userStore.isLoggedIn) {
    loadFavorites()
  }
})
</script>

<template>
  <view class="favorites-page">
    <NavBar title="我的收藏" :show-back="true" />

    <!-- 未登录 -->
    <template v-if="!userStore.isLoggedIn">
      <EmptyState text="请先登录" sub-text="登录后查看收藏的景点" />
      <view class="favorites-login-wrap">
        <button class="favorites-login-btn" @tap="goLogin">去登录</button>
      </view>
    </template>

    <!-- 已登录 -->
    <template v-else>
      <Loading :visible="loading" />

      <scroll-view
        v-if="!loading"
        class="favorites-scroll"
        scroll-y
        enhanced
        :show-scrollbar="false"
      >
        <EmptyState
          v-if="scenicFavorites.length === 0"
          text="暂无收藏"
          sub-text="去发现喜欢的景点吧"
        />

        <view v-for="item in scenicFavorites" :key="item.favorite.id" class="favorites-card-wrap">
          <ScenicCard
            v-if="item.scenic"
            :scenic-id="item.scenic.id"
            :name="item.scenic.name"
            :image-url="item.scenic.image_url"
            :score="item.scenic.score"
            :price="item.scenic.price"
            :category="item.scenic.category"
            :address="item.scenic.address"
            @click="goScenicDetail"
          />
          <view v-else class="favorites-card-fallback">
            <text class="favorites-fallback-text">景点信息加载失败</text>
          </view>
        </view>

        <view style="height: 40rpx;" />
      </scroll-view>
    </template>
  </view>
</template>

<style lang="scss" scoped>
.favorites-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.favorites-scroll {
  flex: 1;
}

.favorites-card-wrap {
  padding: 0 32rpx;
  margin-top: 8rpx;
}

.favorites-card-fallback {
  background: #fff;
  border-radius: 16rpx;
  padding: 80rpx 32rpx;
  text-align: center;
}

.favorites-fallback-text {
  font-size: 28rpx;
  color: #999;
}

.favorites-login-wrap {
  display: flex;
  justify-content: center;
  margin-top: 24rpx;
}

.favorites-login-btn {
  background: #4A90D9;
  color: #fff;
  font-size: 28rpx;
  padding: 12rpx 48rpx;
  border-radius: 32rpx;
}
</style>
