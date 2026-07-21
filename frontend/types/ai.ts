/**
 * AI 相关类型定义（对应后端 app/schemas/ai.py）
 */

// ==================== 后端接口类型 ====================

/** AI 对话请求 */
export interface AIChatRequest {
  message: string
  /**
   * @deprecated 当前后端不使用该字段隔离会话。
   * 后端返回的 session_id 实际是消息 ID（user_message.id），
   * 多轮上下文由后端自动从当前用户最近聊天记录构建。
   * 发送新消息时不要传递此字段。
   */
  session_id?: number
}

/** AI 对话响应 */
export interface AIChatResponse {
  /** @deprecated 实际为本次用户消息的 ID，非会话 ID */
  session_id: number
  user_message: AISessionResponse
  ai_message: AISessionResponse
}

/** AI 聊天记录（服务端返回的单条消息） */
export interface AISessionResponse {
  id: number
  user_id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

// ==================== 前端展示类型 ====================

/**
 * 前端聊天消息 — 扩展服务端 AISessionResponse，
 * 增加本地状态标记以支持发送中 / 失败 / 重试等 UI 状态。
 */
export interface ChatMessage {
  /** 服务端消息 ID（数字）或本地临时 ID（"_local_" 前缀字符串） */
  id: number | string
  role: 'user' | 'assistant'
  content: string
  /** 消息发送状态（仅前端使用） */
  status?: 'sending' | 'sent' | 'failed'
  /** 是否为本地临时消息（尚未经服务端确认） */
  isLocal?: boolean
  /** 服务端创建时间（ISO 字符串） */
  created_at?: string
}
