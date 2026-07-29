/**
 * AI 对话 API 接口（对应后端 /api/ai/*）
 */
import { http, toBody } from './request'
import type {
  AIChatRequest,
  AIChatResponse,
  AISessionResponse,
  PlanGenerateRequest,
} from '@/types/ai'
import type { TravelPlan } from '@/types/travel'

// ==================== 聊天记录 ====================

/** 获取我的 AI 聊天记录列表 */
export function getAISessions(params?: { skip?: number; limit?: number }) {
  return http.get<AISessionResponse[]>('/api/ai/sessions', params)
}

/** 删除聊天记录 */
export function deleteAISession(sessionId: number) {
  return http.delete(`/api/ai/sessions/${sessionId}`)
}

// ==================== AI 对话 ====================

/** 发送 AI 对话消息 */
export function sendChatMessage(data: AIChatRequest) {
  return http.post<AIChatResponse>('/api/ai/chat', toBody(data))
}

// ==================== P3: 旅行计划生成 ====================

/**
 * AI 计划生成专用超时 (ms)
 *
 * AI 生成为长耗时同步操作：Render 冷启动 5-30s + DeepSeek 调用 3-10s + 数据库写入。
 * 需要比普通接口（60s）更长的等待时间。超时后前端将进入结果确认流程。
 */
export const AI_PLAN_GENERATE_TIMEOUT = 120000

/** 生成 AI 旅行计划 */
export function generatePlan(data: PlanGenerateRequest): Promise<TravelPlan> {
  return http.post<TravelPlan>('/api/ai/plans/generate', toBody(data), {
    timeout: AI_PLAN_GENERATE_TIMEOUT,
  })
}
