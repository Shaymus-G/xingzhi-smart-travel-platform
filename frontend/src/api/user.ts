/**
 * 用户 API 接口（对应后端 /api/users/*）
 */
import { http } from './request'
import type {
  User,
  LoginParams,
  RegisterParams,
  LoginResult,
  UpdateUserParams,
  UserPreferenceCreate,
  UserPreferenceResponse,
} from '@/types/user'

// ==================== 认证 ====================

/** 用户注册 */
export function register(data: RegisterParams): Promise<User> {
  return http.post<User>('/api/users/register', data as unknown as Record<string, unknown>)
}

/** 用户登录 */
export function login(data: LoginParams): Promise<LoginResult> {
  return http.post<LoginResult>('/api/users/login', data as unknown as Record<string, unknown>)
}

// ==================== 用户资料 ====================

/** 获取当前用户信息 */
export function getMe(): Promise<User> {
  return http.get<User>('/api/users/me')
}

/** 更新当前用户信息 */
export function updateMe(data: UpdateUserParams): Promise<User> {
  return http.put<User>('/api/users/me', data as unknown as Record<string, unknown>)
}

/** 获取指定用户信息 */
export function getUserById(userId: number): Promise<User> {
  return http.get<User>(`/api/users/${userId}`)
}

// ==================== 用户偏好（保留，本轮页面不使用） ====================

/** 获取我的偏好列表 */
export function getMyPreferences(): Promise<UserPreferenceResponse[]> {
  return http.get<UserPreferenceResponse[]>('/api/users/me/preferences')
}

/** 添加偏好 */
export function addPreference(data: UserPreferenceCreate): Promise<UserPreferenceResponse> {
  return http.post<UserPreferenceResponse>('/api/users/me/preferences', data as unknown as Record<string, unknown>)
}

/** 删除偏好 */
export function removePreference(prefId: number): Promise<void> {
  return http.delete(`/api/users/me/preferences/${prefId}`)
}
