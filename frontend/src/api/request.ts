/**
 * uni.request 封装 — 统一拦截、Token 注入、错误处理
 *
 * 对应后端 app/utils/response.py 的统一响应格式 { code, message, data }
 * 当 code === 0 时，resolve(data)；否则 reject 错误信息。
 */
import { getToken, clearAuthStorage } from '@/utils/storage'

/** 后端 API 基础地址 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/** 请求超时时间 (ms) */
const TIMEOUT = 15000

/**
 * 发起 HTTP 请求
 *
 * @returns Promise<T> — 成功时直接返回 data 字段
 * @throws  Error — 失败时抛出含清晰 message 的错误
 *
 * 用法：
 *   const user = await request<User>('/api/users/me')
 */
export async function request<T = unknown>(
  url: string,
  options: Partial<UniApp.RequestOptions> = {},
): Promise<T> {
  const token = getToken()

  const header: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.header as Record<string, string>) || {}),
  }

  // 注入 JWT
  if (token) {
    header['Authorization'] = `Bearer ${token}`
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}${url}`,
      method: options.method || 'GET',
      data: options.data,
      header,
      timeout: options.timeout || TIMEOUT,
      success(res) {
        const statusCode = res.statusCode
        const body = res.data as Record<string, unknown>

        // 401 / 403 — 清除登录态并跳转登录页
        if (statusCode === 401 || statusCode === 403) {
          clearAuthStorage()
          uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
          uni.reLaunch({ url: '/pages/auth/login' })
          reject(new Error('登录已过期，请重新登录'))
          return
        }

        // FastAPI 校验错误（422）— 提取 detail
        if (statusCode === 422 && body?.detail) {
          const detail = body.detail
          const msg = Array.isArray(detail)
            ? detail.map((d: Record<string, unknown>) => d.msg || '').join('; ')
            : String(detail)
          reject(new Error(msg || '请求参数错误'))
          return
        }

        // 业务成功（code === 0）
        if ((statusCode === 200 || statusCode === 201) && body?.code === 0) {
          resolve(body.data as T)
          return
        }

        // 业务失败（code !== 0）
        if (body?.code !== undefined && body.code !== 0) {
          reject(new Error((body.message as string) || '请求失败'))
          return
        }

        // HTTP 错误状态码
        if (statusCode && statusCode >= 400) {
          const detail = body?.detail as string | undefined
          reject(new Error(detail || `请求失败 (${statusCode})`))
          return
        }

        // 兜底：非标准响应格式
        resolve(body as unknown as T)
      },
      fail(err) {
        reject(new Error(err.errMsg || '网络异常，请检查网络连接'))
      },
    })
  })
}

/**
 * 便捷方法
 */
export const http = {
  get<T = unknown>(url: string, params?: Record<string, unknown>): Promise<T> {
    return request<T>(url, { method: 'GET', data: params })
  },
  post<T = unknown>(url: string, data?: Record<string, unknown>): Promise<T> {
    return request<T>(url, { method: 'POST', data })
  },
  put<T = unknown>(url: string, data?: Record<string, unknown>): Promise<T> {
    return request<T>(url, { method: 'PUT', data })
  },
  delete<T = unknown>(url: string, params?: Record<string, unknown>): Promise<T> {
    return request<T>(url, { method: 'DELETE', data: params })
  },
}
