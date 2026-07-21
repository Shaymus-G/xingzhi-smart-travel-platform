/**
 * 用户相关类型定义（对应后端 app/schemas/user.py）
 */

// ==================== 核心类型 ====================

/** 用户信息 */
export interface User {
  id: number
  username: string
  email: string
  avatar: string | null
  phone: string | null
  api_key?: string | null
  is_active: boolean
  created_at?: string
  updated_at?: string
}

/** 登录请求参数 */
export interface LoginParams {
  username: string
  password: string
}

/** 注册请求参数 */
export interface RegisterParams {
  username: string
  email: string
  password: string
}

/** 登录成功返回 */
export interface LoginResult {
  access_token: string
  token_type: string
  user: User
}

/** 更新用户信息参数 */
export interface UpdateUserParams {
  username?: string
  email?: string
  password?: string
  avatar?: string
  phone?: string
  api_key?: string
  is_active?: boolean
}

// ==================== 偏好（保留，本轮页面不使用） ====================

export interface UserPreferenceCreate {
  preference_type: string
  preference_value: string
  weight?: number
}

export interface UserPreferenceResponse {
  id: number
  user_id: number
  preference_type: string
  preference_value: string
  weight: number
}
