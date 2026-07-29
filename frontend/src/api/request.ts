/**
 * uni.request 封装 — 统一拦截、Token 注入、错误处理
 *
 * 对应后端 app/utils/response.py 的统一响应格式 { code, message, data }
 * 当 code === 0 时，resolve(data)；否则 reject 错误信息。
 */
import { getToken, clearAuthStorage } from '@/utils/storage'
import { getApiBaseUrl } from '@/config/runtime'
import { appendQueryParams, type QueryValue } from '@/utils/query'

/**
 * 后端 API 基础地址 — 运行时动态读取
 *
 * 默认来自 VITE_API_BASE_URL 环境变量。
 * 用户在"高级设置"中手动覆盖后，使用本地存储中的地址。
 * 地址变更后自动清除登录态，避免 Token 泄露。
 */

/**
 * 请求超时时间 (ms)
 *
 * Render 冷启动可能需要 5-30s，DeepSeek API 调用约 3-10s，
 * 因此设置较长的超时以避免 request:fail。
 */
const TIMEOUT = 60000

/** 防止 401 时多次 reLaunch */
let _authRedirecting = false

// ==================== 错误类型 ====================

/** API 层统一错误 — 携带机器可读 code，页面层不应通过中文文本判断错误类型 */
export class ApiError extends Error {
  code: string
  constructor(message: string, code: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

/** 单请求额外配置 */
export interface RequestExtraOptions {
  /** 覆盖全局默认超时 (ms) */
  timeout?: number
  /**
   * URL Query 参数 — 追加到请求 URL 末尾。
   *
   * - undefined 值被跳过
   * - null 值作为空值发送（`key=`）
   * - false / 0 正常发送（不会被误删）
   * - 数组每一项作为独立同名参数
   * - 嵌套对象被跳过
   * - 字符串自动编码
   */
  query?: Record<string, QueryValue>
  /**
   * 是否注入 Authorization header。
   *
   * @default true
   */
  auth?: boolean
  /**
   * 收到 401/403 时是否清除登录态并跳转登录页。
   *
   * @default true — 受保护接口需要跳转
   * 设为 false 用于公开接口（如分享页面），401 仅返回错误不跳转。
   */
  redirectOnUnauthorized?: boolean
}

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
 * @param url     API 路径（相对于 Base URL）
 * @param options uni.request 原生选项（method / data / header 等）
 * @param extra   扩展配置（timeout / query / auth / redirectOnUnauthorized）
 * @returns Promise<T> — 成功时直接返回 data 字段
 * @throws  Error — 失败时抛出含清晰 message 的错误
 *
 * 用法：
 *   const user = await request<User>('/api/users/me')
 *   const plan = await request('/api/ai/plans/generate', { method: 'POST', data: body }, { timeout: 120000 })
 */
export async function request<T = unknown>(
  url: string,
  options: Partial<UniApp.RequestOptions> = {},
  extra: RequestExtraOptions = {},
): Promise<T> {
  // 每次请求动态读取运行时 Base URL
  const baseUrl = getApiBaseUrl()

  if (!baseUrl) {
    return Promise.reject(
      new ApiError('API 地址未配置，请在设置中配置后端地址', 'CONFIG_ERROR'),
    )
  }

  const token = getToken()

  // 解析扩展配置（默认值）
  const shouldAuth = extra.auth !== false
  const shouldRedirect = extra.redirectOnUnauthorized !== false

  const header: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.header as Record<string, string>) || {}),
  }

  // 注入 JWT — 仅当 auth 未显式关闭时
  if (token && shouldAuth) {
    header['Authorization'] = `Bearer ${token}`
  }

  // 附加 Query 参数
  const finalUrl = extra.query
    ? appendQueryParams(url, extra.query)
    : url

  return new Promise((resolve, reject) => {
    // 超时优先级：extra.timeout > options.timeout > 全局 TIMEOUT
    const reqTimeout = extra.timeout ?? options.timeout ?? TIMEOUT
    let _settled = false
    let _reqTask: UniApp.RequestTask | null = null

    const settleReject = (err: Error) => {
      if (_settled) return
      _settled = true
      clearTimeout(timer)
      reject(err)
    }

    const settleResolve = (value: T) => {
      if (_settled) return
      _settled = true
      clearTimeout(timer)
      resolve(value)
    }

    // JS 级超时保护：uni.request 的 timeout 在 H5 模式下可能不生效，
    // 当后端不可达时 Promise 会永久 pending，导致页面 loading 永不结束。
    // 触发后调用 RequestTask.abort() 释放前端连接资源，
    // 但不等于取消服务端任务 — 后端可能仍在处理。
    const timer = setTimeout(() => {
      if (_settled) return
      if (import.meta.env.DEV) {
        console.warn('[request] JS timeout guard fired', {
          url: `${baseUrl}${finalUrl}`,
          timeout: reqTimeout,
        })
      }
      // 先标记 settled 再 abort，防止 abort 触发的 fail 回调覆盖超时错误
      _settled = true
      clearTimeout(timer)
      if (_reqTask && typeof _reqTask.abort === 'function') {
        _reqTask.abort()
      }
      reject(new ApiError('请求超时，请稍后重试', 'REQUEST_TIMEOUT'))
    }, reqTimeout)

    _reqTask = uni.request({
      url: `${baseUrl}${finalUrl}`,
      method: options.method || 'GET',
      data: options.data,
      header,
      timeout: reqTimeout,
      success(res) {
        clearTimeout(timer)
        const statusCode = res.statusCode
        const body = res.data as Record<string, unknown>

        // 401 / 403 — 根据 redirectOnUnauthorized 决定行为
        if (statusCode === 401 || statusCode === 403) {
          if (shouldRedirect) {
            // 受保护请求：清除登录态并跳转登录页（防重入）
            if (!_authRedirecting) {
              _authRedirecting = true
              clearAuthStorage()
              uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
              uni.reLaunch({
                url: '/pages/auth/login',
                complete: () => { _authRedirecting = false },
              })
            }
          }
          // 无论是否跳转，都返回错误给调用方
          settleReject(new ApiError('登录已过期，请重新登录', 'AUTH_EXPIRED'))
          return
        }

        // 204 No Content — 返回 undefined，不访问 response.data
        if (statusCode === 204) {
          settleResolve(undefined as unknown as T)
          return
        }

        // FastAPI 校验错误（422）— 提取 detail
        if (statusCode === 422 && body?.detail) {
          const detail = body.detail
          const msg = Array.isArray(detail)
            ? detail.map((d: Record<string, unknown>) => d.msg || '').join('; ')
            : String(detail)
          settleReject(new ApiError(msg || '请求参数错误', 'VALIDATION_ERROR'))
          return
        }

        // 业务成功（code === 0）
        if ((statusCode === 200 || statusCode === 201) && body?.code === 0) {
          settleResolve(body.data as T)
          return
        }

        // 业务失败（code !== 0）
        if (body?.code !== undefined && body.code !== 0) {
          settleReject(new ApiError((body.message as string) || '请求失败', 'BUSINESS_ERROR'))
          return
        }

        // HTTP 错误状态码
        if (statusCode && statusCode >= 400) {
          const detail = body?.detail as string | undefined
          settleReject(new ApiError(detail || `请求失败 (${statusCode})`, 'HTTP_ERROR'))
          return
        }

        // 兜底：非标准响应格式
        settleResolve(body as unknown as T)
      },
      fail(err) {
        clearTimeout(timer)
        // 开发环境：输出诊断信息（不含敏感数据）
        if (import.meta.env.DEV) {
          console.error('[request] network failure', {
            url: `${baseUrl}${finalUrl}`,
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

        settleReject(new ApiError(message, 'NETWORK_ERROR'))
      },
    })
  })
}

/**
 * 便捷方法
 *
 * http.get<User[]>('/api/users/me')
 * http.post<LoginResult>('/api/users/login', { username, password })
 * http.publicGet<PlanSnapshot>('/api/public/plan-shares/token123')
 */
export const http = {
  get<TRes = unknown>(
    url: string,
    params?: Record<string, unknown>,
    extra?: RequestExtraOptions,
  ): Promise<TRes> {
    return request<TRes>(url, { method: 'GET', data: params }, extra)
  },
  post<TRes = unknown>(
    url: string,
    data?: Record<string, unknown>,
    extra?: RequestExtraOptions,
  ): Promise<TRes> {
    return request<TRes>(url, { method: 'POST', data }, extra)
  },
  put<TRes = unknown>(
    url: string,
    data?: Record<string, unknown>,
    extra?: RequestExtraOptions,
  ): Promise<TRes> {
    return request<TRes>(url, { method: 'PUT', data }, extra)
  },
  delete<TRes = unknown>(
    url: string,
    params?: Record<string, unknown>,
    extra?: RequestExtraOptions,
  ): Promise<TRes> {
    return request<TRes>(url, { method: 'DELETE', data: params }, extra)
  },
  /**
   * 公开 GET 请求 — 不注入 Authorization header，401 不跳转登录页。
   *
   * 用于公开分享页面等无需认证的接口。
   * 等效于 http.get(url, params, { auth: false, redirectOnUnauthorized: false })
   */
  publicGet<TRes = unknown>(
    url: string,
    params?: Record<string, unknown>,
    extra?: RequestExtraOptions,
  ): Promise<TRes> {
    return request<TRes>(url, { method: 'GET', data: params }, {
      ...extra,
      auth: false,
      redirectOnUnauthorized: false,
    })
  },
}
