/**
 * AI 对话 API 接口（对应后端 /api/ai/*）
 */
import { http } from './request'
import type {
  AIChatRequest,
  AIChatResponse,
  AISessionResponse,
} from '@/types/ai'

// ==================== 聊天记录 ====================

/** 获取我的 AI 聊天记录列表 */
export function getAISessions(params?: { skip?: number; limit?: number }) {
  return http.get<AISessionResponse[]>('/api/ai/sessions', params as unknown as Record<string, unknown>)
}

/** 删除聊天记录 */
export function deleteAISession(sessionId: number) {
  return http.delete(`/api/ai/sessions/${sessionId}`)
}

// ==================== AI 对话 ====================

/** 发送 AI 对话消息 */
export function sendChatMessage(data: AIChatRequest) {
  return http.post<AIChatResponse>('/api/ai/chat', data as unknown as Record<string, unknown>)
}
