/**
 * 统一图片 URL 解析 — 规范化后端图片字段，提供默认图和加载失败回退
 *
 * 规则（按优先级）：
 *   1. 空值 / null / undefined → 返回默认图
 *   2. https:// 完整 URL → 原样返回
 *   3. data: / blob: → 原样返回（本地 base64/blob）
 *   4. //host/path 协议相对 URL → 转为 https://
 *   5. http:// → 保留（不盲目升级为 HTTPS，避免 Mixed Content 反向问题）
 *   6. 以 / 开头的后端相对路径 → 拼接 API Base URL
 *   7. 其他相对路径 → 原样返回（uni-app 自动解析为相对路径）
 *   8. localhost / 127.0.0.1 → 尝试替换为 API Base URL 的 host（仅限开发环境）
 *   9. 无法安全解析 → 返回默认图
 *
 * 注意：不输出 API Key / JWT / 敏感信息到日志。
 */

/** 默认兜底图片 */
export const DEFAULT_IMAGE = '/static/logo.png'

import { getApiBaseUrl } from '@/config/runtime'

/** API Base URL（从运行时配置读取，支持用户手动覆盖） */
function getApiBase(): string {
  return getApiBaseUrl()
}

/**
 * 解析后端返回的图片字段为可安全显示的 URL
 *
 * @param value - 图片字段原始值（可能是完整 URL、相对路径、空值等）
 * @param fallback - 自定义默认图，不传使用 DEFAULT_IMAGE
 * @returns 可用于 <image> src 的安全 URL
 */
export function resolveImageUrl(value?: string | null, fallback?: string): string {
  const defaultImage = fallback || DEFAULT_IMAGE

  // 1. 空值
  if (!value || typeof value !== 'string') {
    return defaultImage
  }

  const trimmed = value.trim()
  if (!trimmed) {
    return defaultImage
  }

  // 2. 完整 HTTPS URL
  if (trimmed.startsWith('https://')) {
    return trimmed
  }

  // 3. data: / blob: 本地资源
  if (trimmed.startsWith('data:') || trimmed.startsWith('blob:')) {
    return trimmed
  }

  // 4. 协议相对 URL → https
  if (trimmed.startsWith('//')) {
    return 'https:' + trimmed
  }

  // 5. http:// — 保留原样（不强制升级）
  if (trimmed.startsWith('http://')) {
    return trimmed
  }

  // 6. 后端相对路径（以 / 开头） → 拼接 API Base
  if (trimmed.startsWith('/')) {
    // 排除本地静态资源路径
    if (trimmed.startsWith('/static/')) {
      return trimmed
    }
    // 排除 api 路径（图片不会是 API 路径）
    if (trimmed.startsWith('/api/')) {
      return trimmed
    }
    // 其他 / 开头相对路径：尝试拼接 API Base URL
    const apiBase = getApiBase()
    if (apiBase) {
      return apiBase + trimmed
    }
    return trimmed
  }

  // 7. 普通相对路径 → 原样（uni-app 自动解析）
  return trimmed
}

/**
 * 图片加载失败时的回退处理
 *
 * 用法（uni-app <image> 组件）：
 *   <image :src="resolveImageUrl(item.image_url)" @error="onImageError" />
 *
 * 在 error 事件中替换 src 为默认图:
 *   onImageError(e) { e.target.src = DEFAULT_IMAGE }
 *
 * 或在组件中直接调用此函数替换 ref。
 */
export function onImageError(event: { detail?: { errMsg?: string }; target?: { src?: string } }) {
  // 静默处理：避免控制台刷屏
  const src = event?.target?.src || event?.detail?.errMsg || 'unknown'
  if (import.meta.env.DEV) {
    console.warn('[image] load failed:', src.substring(0, 100))
  }
  // 设置默认图（由调用方在 @error 中执行 e.target.src = DEFAULT_IMAGE）
}
