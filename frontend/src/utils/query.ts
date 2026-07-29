/**
 * URL Query 参数构造工具
 *
 * 纯字符串实现，不依赖 URLSearchParams / URL / window / document。
 * 在 uni-app H5 和 App 运行时行为一致。
 */

// ==================== 类型 ====================

export type QueryValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | Array<string | number | boolean | null | undefined>

// ==================== 内部辅助 ====================

/**
 * 将单个 Query 值转为 param=value 字符串数组
 *
 * - undefined → 跳过（不产生参数）
 * - null      → key=（空值参数）
 * - false     → key=false
 * - 0         → key=0
 * - 数组       → 展开为多个同名参数
 * - 对象       → 跳过（不序列化 [object Object]）
 * - 其他       → key=encodeURIComponent(String(value))
 */
function serializeValue(key: string, value: unknown): string[] {
  if (value === undefined) return []

  if (Array.isArray(value)) {
    const results: string[] = []
    for (const item of value) {
      results.push(...serializeValue(key, item))
    }
    return results
  }

  if (value === null) {
    // null: 发送空值参数
    return [`${encodeURIComponent(key)}=`]
  }

  if (typeof value === 'object') {
    // 跳过嵌套对象
    return []
  }

  return [`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`]
}

// ==================== 公开 API ====================

/**
 * 安全拼接 URL Query 参数
 *
 * @param url   基础 URL（可已包含 ? 参数）
 * @param query 参数对象
 * @returns     拼接后的完整 URL。空 Query 时返回原 URL。
 *
 * 规则：
 *   - undefined → 跳过
 *   - null      → 空值（`key=`）
 *   - false / 0 → 正常发送
 *   - 数组       → 多个同名参数（`key=v1&key=v2`）
 *   - 对象       → 跳过
 *   - key + value 均使用 encodeURIComponent 编码
 *   - 原 URL 已有 ? 时使用 & 连接
 *
 * 示例：
 *   appendQueryParams('/api/items', { page: 1, tag: null })
 *   → '/api/items?page=1&tag='
 *
 *   appendQueryParams('/api/items?sort=name', { page: 2 })
 *   → '/api/items?sort=name&page=2'
 */
export function appendQueryParams(
  url: string,
  query?: Record<string, QueryValue>,
): string {
  if (!query) return url

  const parts: string[] = []

  for (const [key, value] of Object.entries(query)) {
    parts.push(...serializeValue(key, value))
  }

  if (parts.length === 0) return url

  const qs = parts.join('&')
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}${qs}`
}
