/**
 * uni.request 封装 — 统一拦截、Token 注入、错误处理
 *
 * 对应后端 app/utils/response.py 的统一响应格式 { code, message, data }
 * 当 code === 0 时，resolve(data)；否则 reject 错误信息。
 */
import { getToken, clearAuthStorage } from '@/utils/storage'

/**
 * 后端 API 基础地址 — 从环境变量读取，不硬编码
 *
 * 开发环境：VITE_API_BASE_URL=http://localhost:8000
 * 生产环境：在部署平台配置环境变量
 */
const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '')
  .trim()
  .replace(/\/+$/, '')

/**
 * 请求超时时间 (ms)
 *
 * Render 冷启动可能需要 5-30s，DeepSeek API 调用约 3-10s，
 * 因此设置较长的超时以避免 request:fail。
 */
const TIMEOUT = 60000

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
  // 环境变量缺失时尽早失败，给出明确错误信息
  if (!BASE_URL) {
    return Promise.reject(
      new Error('VITE_API_BASE_URL 未配置，请检查 frontend/.env.development'),
    )
  }

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
        // 开发环境：输出诊断信息（不含敏感数据）
        if (import.meta.env.DEV) {
          console.error('[request] network failure', {
            url: `${BASE_URL}${url}`,
            method: options.method || 'GET',
            errMsg: err.errMsg,
          })
        }

        // 转换为用户可理解的错误信息
        const rawMsg = err.errMsg || ''
        let message: string
        if (rawMsg.includes('timeout') || rawMsg.includes('超时')) {
          message = '请求超时，请稍后重试'
        } else if (rawMsg.includes('fail') || rawMsg.includes('network') || rawMsg.includes('abort')) {
          message = '网络请求失败，请检查网络或服务状态'
        } else {
          message = rawMsg || '网络异常，请检查网络连接'
        }

        reject(new Error(message))
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
