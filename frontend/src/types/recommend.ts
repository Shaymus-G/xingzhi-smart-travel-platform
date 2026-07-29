/**
 * 推荐城市相关类型定义（对应后端 /api/recommend/* 接口）
 *
 * 注意：
 *  - 推荐接口返回 city_id / city_name，与 City 类型的 id / name 不同
 *  - 不继承现有 City 类型，因为字段命名和可选性差异较大
 *  - score / distance_km 可能被序列化为 number 或 string，但前端统一按 number 处理
 */

// ==================== 原始接口类型 ====================

/** 推荐城市基础字段（所有推荐接口共享） */
export interface RecommendCityBase {
  city_id: number
  city_name: string
  province?: string | null
  level?: string | null
  cover_image?: string | null
  /** 周边城市距离（仅 nearby 返回） */
  distance_km?: number | null
  /** 推荐评分（similar / contrast / collaborative 返回） */
  score?: number | null
  /** 推荐理由（similar / contrast / collaborative 返回） */
  reason?: string | null
}

/** 周边城市推荐（nearby） */
export interface NearbyRecommendCity extends RecommendCityBase {}

/** 相似城市推荐（similar） */
export interface SimilarRecommendCity extends RecommendCityBase {}

/** 反差城市推荐（contrast） */
export interface ContrastRecommendCity extends RecommendCityBase {}

/** 协同过滤推荐（collaborative） */
export interface CollaborativeRecommendCity extends RecommendCityBase {}

/** 推荐城市联合类型 */
export type RecommendCity =
  | NearbyRecommendCity
  | SimilarRecommendCity
  | ContrastRecommendCity
  | CollaborativeRecommendCity

/** 推荐来源标识 — 表示推荐区域上下文，非城市数据自身属性 */
export type RecommendationVariant =
  | 'nearby'
  | 'similar'
  | 'contrast'
  | 'collaborative'

// ==================== 标准化视图模型 ====================

/**
 * 标准化推荐城市 — 页面/组件可消费的视图模型
 *
 * 保留数值类型，不做格式化（展示格式由 UI 层负责）。
 * 保留 null（区分"无值"和"0"）。
 */
export interface NormalizedRecommendCity {
  id: number
  name: string
  province: string | null
  level: string | null
  coverImage: string | null
  distanceKm: number | null
  score: number | null
  reason: string | null
}
