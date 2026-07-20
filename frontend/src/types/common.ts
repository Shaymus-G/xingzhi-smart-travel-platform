/**
 * 统一 API 响应格式（对应后端 app/utils/response.py）
 */
export interface APIResponse<T = unknown> {
  /** 状态码，0 表示成功 */
  code: number
  /** 提示信息 */
  message: string
  /** 响应数据 */
  data: T
}

/**
 * 分页请求参数
 */
export interface PaginationParams {
  skip?: number
  limit?: number
}

/**
 * 分页响应
 */
export interface PaginatedData<T> {
  items: T[]
  total: number
}
