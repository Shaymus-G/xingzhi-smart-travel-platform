/**
 * AI 相关类型定义（对应后端 app/schemas/ai.py）
 */

/** AI 对话请求 */
export interface AIChatRequest {
  message: string
  session_id?: number
}

/** AI 对话响应 */
export interface AIChatResponse {
  session_id: number
  user_message: AISessionResponse
  ai_message: AISessionResponse
}

/** AI 聊天记录 */
export interface AISessionResponse {
  id: number
  user_id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

// ==================== P3: 旅行计划生成 ====================

/** AI 旅行计划生成请求 */
export interface PlanGenerateRequest {
  destination: string
  days: number
  budget?: number | null
  travelers?: number
  preferences?: string[]
  start_date?: string | null
  notes?: string | null
}
