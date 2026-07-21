/**
 * 运行时 API 配置 — 支持移动端真机联调和生产环境切换
 *
 * 地址优先级：
 *   1. 用户在高级设置中保存的本地覆盖（uni.storage）
 *   2. 环境变量 VITE_API_BASE_URL（.env.development / .env.production）
 *
 * 移动端真机联调指南：
 *   手机和电脑连接同一 WiFi → 电脑防火墙允许入站端口 8000
 *   → uvicorn 监听 0.0.0.0 → 手机访问 http://<电脑局域网IP>:8000
 *   → 在高级设置中填入该地址并测试连接 → 确认后自动切换。
 *
 * API 地址变更后会自动清除登录态，避免 Token 泄露到错误服务器。
 */
import { getToken, removeToken, removeUserInfo } from '@/utils/storage'

/** 本地存储键（用户手动覆盖的 API 地址） */
const STORAGE_KEY = 'XINGZHI_API_BASE_URL'

/** 环境变量默认值 */
export function getDefaultApiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL ?? '')
    .trim()
    .replace(/\/+$/, '')
}

/**
 * 获取当前生效的 API Base URL
 * 用户手动覆盖优先，否则使用环境变量默认值。
 */
export function getApiBaseUrl(): string {
  try {
    const override = uni.getStorageSync(STORAGE_KEY)
    if (override && typeof override === 'string' && override.trim()) {
      return override.trim().replace(/\/+$/, '')
    }
  } catch {
    // storage 不可用时静默回退
  }
  return getDefaultApiBaseUrl()
}

/** 验证结果 */
export interface ValidationResult {
  valid: boolean
  error?: string
}

/**
 * 验证 API Base URL 格式
 *
 * 规则：
 *   - 不能为空
 *   - 不能包含 /api 路径（防止 /api/api/... 双写）
 *   - 远程地址必须使用 HTTPS
 *   - 本地调试允许 HTTP（localhost / 127.0.0.1 / 局域网 IP）
 */
export function validateApiBaseUrl(url: string): ValidationResult {
  const trimmed = url.trim().replace(/\/+$/, '')

  if (!trimmed) {
    return { valid: false, error: '地址不能为空' }
  }

  // 检查是否误填了 /api 路径
  if (/\/api\/?$/.test(trimmed)) {
    return { valid: false, error: '请移除末尾的 /api，系统会自动拼接接口路径' }
  }

  // 必须是 http 或 https
  if (!/^https?:\/\//i.test(trimmed)) {
    return { valid: false, error: '地址必须以 http:// 或 https:// 开头' }
  }

  // 远程地址强制 HTTPS（本地回环和局域网除外）
  const isLocal =
    trimmed.startsWith('http://127.') ||
    trimmed.startsWith('http://10.') ||
    trimmed.startsWith('http://172.1') ||  // 172.16-172.31
    trimmed.startsWith('http://192.168.')

  if (trimmed.startsWith('http://') && !isLocal) {
    return { valid: false, error: '远程服务器必须使用 HTTPS，本地调试允许 HTTP' }
  }

  return { valid: true }
}

/**
 * 保存用户手动覆盖的 API 地址
 *
 * 副作用：
 *   - 清除 JWT Token 和用户缓存（防止旧 Token 发送到新服务器）
 *   - 要求用户重新登录
 */
export function setApiBaseUrl(url: string): void {
  const trimmed = url.trim().replace(/\/+$/, '')
  const current = getApiBaseUrl()

  if (trimmed === current) return

  uni.setStorageSync(STORAGE_KEY, trimmed)

  // 地址变更 → 清除登录态
  removeToken()
  removeUserInfo()
}

/** 恢复为环境变量默认地址 */
export function resetApiBaseUrl(): void {
  try {
    uni.removeStorageSync(STORAGE_KEY)
  } catch {
    // 静默
  }
  // 同样需要清除登录态
  removeToken()
  removeUserInfo()
}

/** 是否为用户手动覆盖（非环境变量默认） */
export function isApiBaseUrlOverridden(): boolean {
  try {
    const override = uni.getStorageSync(STORAGE_KEY)
    return !!override && typeof override === 'string' && override.trim().length > 0
  } catch {
    return false
  }
}

/**
 * 测试与指定 API 地址的连接
 *
 * 调用健康检查端点，不携带 JWT（防止 Token 泄露到错误服务器）。
 * 超时时间 5 秒。
 */
export function testApiConnection(url: string): Promise<{ ok: boolean; error?: string }> {
  const base = url.trim().replace(/\/+$/, '')
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      resolve({ ok: false, error: '连接超时，请检查地址和网络' })
    }, 5000)

    uni.request({
      url: `${base}/api/health`,
      method: 'GET',
      timeout: 5000,
      success(res) {
        clearTimeout(timer)
        if (res.statusCode === 200) {
          resolve({ ok: true })
        } else {
          resolve({ ok: false, error: `服务器返回 ${res.statusCode}` })
        }
      },
      fail(err) {
        clearTimeout(timer)
        resolve({ ok: false, error: err.errMsg || '无法连接服务器' })
      },
    })
  })
}
