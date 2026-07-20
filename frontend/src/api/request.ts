/**
 * uni.request 封装 — 统一拦截、Token 注入、错误处理
 *
 * 对应后端 app/utils/response.py 的统一响应格式 { code, message, data }
 * 当 code === 0 时，resolve(data)；否则 reject 错误信息。
 */
import { getToken, clearAuthStorage } from '@/utils/storage'

/** 后端 API 基础地址 */
const BASE_URL = 'https://xingzhi-smart-travel-platform.onrender.com'

/** 请求超时时间 (ms) */
const TIMEOUT = 15000

/** 防止 401 时多次 reLaunch */
let _authRedirecting = false

/**
 * 类型桥接辅助 — 将任意接口类型转为 Record<string, unknown>
 *
 * TypeScript 严格模式下，不带索引签名的 interface/type 无法直接赋值给
 * Record<string, unknown>，此函数在 http 层集中处理转换。
 */
export function toBody<T>(data: T): Record<string, unknown> {
  return data as unknown as Record<string, unknown>
}

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

        // 401 / 403 — 清除登录态并跳转登录页（防重入）
        if (statusCode === 401 || statusCode === 403) {
          if (!_authRedirecting) {
            _authRedirecting = true
            clearAuthStorage()
            uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
            uni.reLaunch({
              url: '/pages/auth/login',
              complete: () => { _authRedirecting = false },
            })
          }
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
        console.error('[request] network error:', JSON.stringify(err))
        reject(new Error(err.errMsg || '网络异常，请检查网络连接'))
      },
    })
  })
}

/**
 * 便捷方法
 *
 * http.get<User[]>('/api/users/me')
 * http.post<LoginResult>('/api/users/login', { username, password })
 */
export const http = {
  get<TRes = unknown>(url: string, params?: Record<string, unknown>): Promise<TRes> {
    return request<TRes>(url, { method: 'GET', data: params })
  },
  post<TRes = unknown>(url: string, data?: Record<string, unknown>): Promise<TRes> {
    return request<TRes>(url, { method: 'POST', data })
  },
  put<TRes = unknown>(url: string, data?: Record<string, unknown>): Promise<TRes> {
    return request<TRes>(url, { method: 'PUT', data })
  },
  delete<TRes = unknown>(url: string, params?: Record<string, unknown>): Promise<TRes> {
    return request<TRes>(url, { method: 'DELETE', data: params })
  },
}
