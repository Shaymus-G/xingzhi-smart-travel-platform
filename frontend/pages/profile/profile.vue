<script setup lang="ts">
/**
 * 个人中心页面（TabBar 页面）
 * 展示用户信息、常用入口、退出登录
 */
import { onShow } from '@dcloudio/uni-app'
import NavBar from '@/components/NavBar.vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 每次显示时刷新登录态
onShow(() => {
  userStore.initAuthFromStorage()
})

/** 跳转登录页 */
function goLogin() {
  uni.navigateTo({ url: '/pages/auth/login' })
}

/** 退出登录 */
function handleLogout() {
  uni.showModal({
    title: '确认退出',
    content: '退出后需要重新登录',
    success(res) {
      if (res.confirm) {
        userStore.logout()
        uni.showToast({ title: '已退出登录', icon: 'success' })
      }
    },
  })
}

/** 菜单项类型 */
interface MenuItem {
  icon: string
  title: string
  path: string
}

const menuItems: MenuItem[] = [
  { icon: '📋', title: '我的旅行计划', path: '/pages/plan/list' },
  { icon: '❤️', title: '我的收藏', path: '/pages/profile/favorites' },
  { icon: '⭐', title: '我的评论', path: '' },
  { icon: '⚙️', title: '偏好设置', path: '' },
]

function handleMenuTap(item: MenuItem) {
  if (item.path) {
    uni.navigateTo({ url: item.path })
  } else {
    uni.showToast({ title: '功能开发中', icon: 'none' })
  }
}
</script>

<template>
  <view class="profile-page">
    <NavBar title="个人中心" />

    <!-- 用户信息区域 -->
    <view class="profile-header">
      <image class="profile-avatar" src="/static/logo.png" mode="aspectFill" />
      <template v-if="userStore.isLoggedIn && userStore.userInfo">
        <text class="profile-name">{{ userStore.userInfo.username }}</text>
        <text class="profile-email">{{ userStore.userInfo.email }}</text>
      </template>
      <template v-else>
        <text class="profile-name">未登录</text>
        <button class="profile-login-btn" @tap="goLogin">立即登录</button>
      </template>
    </view>

    <!-- 菜单列表 -->
    <view class="profile-menu">
      <view
        v-for="item in menuItems"
        :key="item.title"
        class="profile-menu-item"
        @tap="handleMenuTap(item)"
      >
        <text class="profile-menu-icon">{{ item.icon }}</text>
        <text class="profile-menu-title">{{ item.title }}</text>
        <text class="profile-menu-arrow">›</text>
      </view>
    </view>

    <!-- 退出登录 -->
    <view v-if="userStore.isLoggedIn" class="profile-logout" @tap="handleLogout">
      <text>退出登录</text>
    </view>

    <!-- 版本号 -->
    <text class="profile-version">行知 v1.0.0</text>
  </view>
</template>

<style lang="scss" scoped>
.profile-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.profile-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48rpx 0;
  background: #fff;
}

.profile-avatar {
  width: 140rpx;
  height: 140rpx;
  border-radius: 50%;
  background: #f0f0f0;
  margin-bottom: 20rpx;
}

.profile-name {
  font-size: 34rpx;
  font-weight: 600;
  color: #333;
}

.profile-email {
  font-size: 26rpx;
  color: #999;
  margin-top: 8rpx;
}

.profile-login-btn {
  margin-top: 16rpx;
  background: #4A90D9;
  color: #fff;
  font-size: 28rpx;
  padding: 12rpx 40rpx;
  border-radius: 32rpx;
}

.profile-menu {
  margin-top: 16rpx;
  background: #fff;
}

.profile-menu-item {
  display: flex;
  align-items: center;
  padding: 28rpx 32rpx;
  border-bottom: 1rpx solid #f5f5f5;
}

.profile-menu-icon {
  font-size: 36rpx;
  margin-right: 20rpx;
}

.profile-menu-title {
  flex: 1;
  font-size: 30rpx;
  color: #333;
}

.profile-menu-arrow {
  font-size: 36rpx;
  color: #ccc;
}

.profile-logout {
  margin: 32rpx;
  padding: 24rpx;
  text-align: center;
  background: #fff;
  border-radius: 12rpx;
  font-size: 30rpx;
  color: #FF4D4F;
}

.profile-version {
  display: block;
  text-align: center;
  font-size: 24rpx;
  color: #ccc;
  padding-bottom: 40rpx;
}
</style>
