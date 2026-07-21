/**
 * 用户状态管理 — 登录态、用户信息、Token
 *
 * 对接后端 /api/users/* 认证接口。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginParams, RegisterParams } from '@/types/user'
import * as userApi from '@/api/user'
import {
  getToken,
  setToken,
  getUserInfo,
  setUserInfo,
  clearAuthStorage,
} from '@/utils/storage'

export const useUserStore = defineStore('user', () => {
  // ========== 状态 ==========
  const token = ref<string>(getToken())
  const userInfo = ref<User | null>(getUserInfo<User>())
  const loading = ref(false)

  // ========== 计算属性 ==========
  const isLoggedIn = computed(() => !!token.value && !!userInfo.value)

  // ========== 内部方法 ==========

  /** 同步 token 到 store 和 storage */
  function _setToken(newToken: string) {
    token.value = newToken
    setToken(newToken)
  }

  /** 同步 userInfo 到 store 和 storage */
  function _setUserInfo(user: User) {
    userInfo.value = user
    setUserInfo(user)
  }

  // ========== Actions ==========

  /**
   * 从本地存储恢复登录态
   * App 启动时 / 个人中心 onShow 时调用
   */
  async function initAuthFromStorage() {
    const savedToken = getToken()
    if (!savedToken) {
      token.value = ''
      userInfo.value = null
      return
    }

    token.value = savedToken

    // 尝试从 storage 恢复用户信息（快速展示）
    const cachedUser = getUserInfo<User>()
    if (cachedUser) {
      userInfo.value = cachedUser
    }

    // 向服务端校验 token 有效性
    try {
      await fetchMe()
    } catch {
      // token 已失效，清除登录态
      clearAuthStorage()
      token.value = ''
      userInfo.value = null
    }
  }

  /**
   * 登录
   */
  async function loginAction(params: LoginParams): Promise<void> {
    loading.value = true
    try {
      const result = await userApi.login(params)
      _setToken(result.access_token)
      _setUserInfo(result.user)
    } finally {
      loading.value = false
    }
  }

  /**
   * 注册
   * 注册成功不自动登录，由页面跳转登录页
   */
  async function registerAction(params: RegisterParams): Promise<User> {
    loading.value = true
    try {
      return await userApi.register(params)
    } finally {
      loading.value = false
    }
  }

  /**
   * 从服务端获取最新用户信息
   */
  async function fetchMe(): Promise<void> {
    const user = await userApi.getMe()
    _setUserInfo(user)
  }

  /**
   * 登出
   * 清除 store 和 storage，不跳转页面（由页面决定后续行为）
   */
  function logout() {
    token.value = ''
    userInfo.value = null
    clearAuthStorage()
  }

  return {
    // 状态
    token,
    userInfo,
    loading,
    // 计算属性
    isLoggedIn,
    // 方法
    initAuthFromStorage,
    loginAction,
    registerAction,
    fetchMe,
    logout,
  }
})
