/**
 * 本地存储工具 — uni.storage 封装
 *
 * 统一管理所有持久化 key，避免各处写死字符串。
 */

// ========== Storage Key 常量 ==========
const TOKEN_KEY = 'access_token'
const USER_INFO_KEY = 'user_info'

// ========== Token ==========

export function getToken(): string {
  return uni.getStorageSync(TOKEN_KEY) || ''
}

export function setToken(token: string): void {
  uni.setStorageSync(TOKEN_KEY, token)
}

export function removeToken(): void {
  uni.removeStorageSync(TOKEN_KEY)
}

// ========== 用户信息 ==========

export function getUserInfo<T = Record<string, unknown>>(): T | null {
  try {
    const raw = uni.getStorageSync(USER_INFO_KEY)
    if (!raw) return null
    return JSON.parse(raw) as T
  } catch {
    // JSON 解析失败时静默返回 null
    return null
  }
}

export function setUserInfo(user: unknown): void {
  uni.setStorageSync(USER_INFO_KEY, JSON.stringify(user))
}

export function removeUserInfo(): void {
  uni.removeStorageSync(USER_INFO_KEY)
}

// ========== 批量清除 ==========

/** 清除所有认证相关存储（登出时调用） */
export function clearAuthStorage(): void {
  removeToken()
  removeUserInfo()
}
