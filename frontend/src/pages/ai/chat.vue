<script setup lang="ts">
/**
 * AI 对话页面 — 接入后端 DeepSeek 真实接口
 *
 * 功能：
 *  - 登录保护（onShow + 发送前）
 *  - 历史消息加载（去重、失败降级）
 *  - 消息发送 / 失败标记 / 重试
 *  - 自动滚动到底部
 *  - 页面生命周期保护
 */
import { ref, nextTick } from 'vue'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
import NavBar from '@/components/NavBar.vue'
import { sendChatMessage, getAISessions, deleteAISession } from '@/api/ai'
import { useUserStore } from '@/stores/user'
import type { ChatMessage } from '@/types/ai'
import { markdownToHtml } from '@/utils/markdown'

const userStore = useUserStore()

// ========== 消息状态 ==========
const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const isSending = ref(false)

// ========== 历史加载状态 ==========
const historyLoading = ref(false)
const historyLoaded = ref(false)
const historyError = ref('')

// ========== 删除状态 ==========
const deletingIds = ref<Set<number | string>>(new Set())

function isDeleting(id: number | string): boolean {
  return deletingIds.value.has(id)
}

// ========== 滚动 ==========
const scrollIntoViewId = ref('')
const SCROLL_ANCHOR = 'chat-bottom-anchor'

// ========== 生命周期 ==========
let pageActive = false
let localIdCounter = 0

// ========== 本地消息 ID 工具 ==========
function nextLocalId(): string {
  return `_local_${Date.now()}_${++localIdCounter}`
}

function isLocalId(id: number | string): boolean {
  return typeof id === 'string' && id.startsWith('_local_')
}

// ========== 欢迎消息 ==========
function ensureWelcomeMessage() {
  if (messages.value.length === 0) {
    messages.value.push({
      id: 0,
      role: 'assistant',
      content: '你好！我是行知 AI 旅行助手，有什么可以帮助你的吗？',
    })
  }
}

// ========== 历史消息加载 ==========
async function loadHistory() {
  if (historyLoading.value || !userStore.isLoggedIn) return

  historyLoading.value = true
  historyError.value = ''

  try {
    const sessions = await getAISessions({ limit: 50 })

    if (!pageActive) return

    // 构建已有服务端消息 ID 集合（用于去重）
    const existingServerIds = new Set(
      messages.value
        .filter(m => !isLocalId(m.id) && m.id !== 0)
        .map(m => m.id as number),
    )

    // 转换并过滤：仅保留 user/assistant 角色，去重
    const newMessages: ChatMessage[] = sessions
      .filter(s => !existingServerIds.has(s.id))
      .map(s => {
        const role = s.role === 'assistant' ? 'assistant' as const : 'user' as const
        return {
          id: s.id,
          role,
          content: s.content,
          status: 'sent' as const,
          created_at: s.created_at,
        }
      })

    if (newMessages.length > 0) {
      // 移除纯本地欢迎消息，用真实历史替换
      messages.value = messages.value.filter(m => m.id !== 0)
      // 合并并按服务端 ID 排序（本地消息排在最后）
      messages.value = [...messages.value, ...newMessages].sort((a, b) => {
        const aNum = typeof a.id === 'number' ? a.id : Number.MAX_SAFE_INTEGER
        const bNum = typeof b.id === 'number' ? b.id : Number.MAX_SAFE_INTEGER
        return aNum - bNum
      })
    }

    ensureWelcomeMessage()
    historyLoaded.value = true
  } catch (err) {
    if (!pageActive) return
    const msg = err instanceof Error ? err.message : '加载历史记录失败'
    historyError.value = msg
    ensureWelcomeMessage()
  } finally {
    if (pageActive) {
      historyLoading.value = false
      scrollToBottom()
    }
  }
}

// ========== 滚动到底部 ==========
function scrollToBottom() {
  // 先清空再设置，确保重复滚动仍然触发
  scrollIntoViewId.value = ''
  nextTick(() => {
    scrollIntoViewId.value = SCROLL_ANCHOR
  })
}

// ========== 跳转旅行计划生成页 ==========
function goToGeneratePlan() {
  if (!userStore.isLoggedIn) {
    uni.showToast({
      title: '请先登录',
      icon: 'none',
    })
    uni.navigateTo({
      url: '/pages/auth/login',
    })
    return
  }

  uni.navigateTo({
    url: '/pages/plan/generate',
  })
}

// ========== 删除会话 ==========
async function confirmDeleteSession(msg: ChatMessage, event?: any) {
  // 阻止事件冒泡，避免同时触发消息点击
  event?.stopPropagation?.()

  const sessionId = msg.id
  if (isLocalId(sessionId) || sessionId === 0 || typeof sessionId !== 'number') return

  // 构建确认提示文案
  const preview = msg.content.length > 30
    ? msg.content.slice(0, 30) + '...'
    : msg.content

  try {
    const res = await uni.showModal({
      title: '删除对话',
      content: `确定删除该 AI 对话吗？\n\n"${preview}"\n\n删除后无法恢复。`,
      confirmText: '删除',
      cancelText: '取消',
      confirmColor: '#FF4D4F',
    })

    if (!res.confirm) return

    await doDeleteSession(sessionId)
  } catch {
    // 用户取消或其他情况，不执行删除
  }
}

async function doDeleteSession(sessionId: number) {
  if (isDeleting(sessionId)) return

  deletingIds.value = new Set([...deletingIds.value, sessionId])

  try {
    await deleteAISession(sessionId)

    if (!pageActive) return

    // 从本地消息列表移除
    messages.value = messages.value.filter(m => m.id !== sessionId)

    // 如果删除后没有历史消息了，显示欢迎消息
    const hasServerMessages = messages.value.some(m => !isLocalId(m.id) && m.id !== 0)
    if (!hasServerMessages) {
      messages.value = [{
        id: 0,
        role: 'assistant',
        content: '你好！我是行知 AI 旅行助手，有什么可以帮助你的吗？',
      }]
    }

    uni.showToast({ title: '已删除', icon: 'success', duration: 1500 })
  } catch (err) {
    if (!pageActive) return

    const statusCode = (err as any)?.statusCode || (err as any)?.code
    let msg = '删除失败，请稍后重试'

    if (statusCode === 401) {
      msg = '登录已失效，请重新登录'
    } else if (statusCode === 403) {
      msg = '没有权限删除该对话'
    } else if (statusCode === 404) {
      // 服务端已不存在，从本地列表移除
      messages.value = messages.value.filter(m => m.id !== sessionId)
      msg = '该记录已不存在'
    } else if (statusCode === 500 || statusCode === 503) {
      msg = '服务暂时不可用，请稍后重试'
    } else if (err instanceof Error && err.message) {
      msg = err.message
    }

    uni.showToast({ title: msg, icon: 'none', duration: 2500 })
  } finally {
    if (pageActive) {
      const next = new Set(deletingIds.value)
      next.delete(sessionId)
      deletingIds.value = next
    }
  }
}

// ========== 发送消息（内部，不含登录检查） ==========
async function doSend(text: string, existingLocalId?: string) {
  if (!text.trim() || isSending.value) return

  isSending.value = true

  let localMsg: ChatMessage

  if (existingLocalId) {
    // 重试已有失败消息
    const idx = messages.value.findIndex(m => m.id === existingLocalId)
    if (idx === -1) {
      isSending.value = false
      return
    }
    messages.value[idx] = { ...messages.value[idx], status: 'sending' }
    localMsg = messages.value[idx]
  } else {
    // 新建本地用户消息
    localMsg = {
      id: nextLocalId(),
      role: 'user',
      content: text,
      status: 'sending',
      isLocal: true,
    }
    messages.value.push(localMsg)
  }

  inputText.value = ''
  scrollToBottom()

  try {
    // 不传递 session_id — 后端自动构建上下文
    const response = await sendChatMessage({ message: text })

    if (!pageActive) return

    // 用服务端用户消息替换本地临时消息
    const serverUserMsg: ChatMessage = {
      id: response.user_message.id,
      role: 'user',
      content: response.user_message.content,
      status: 'sent',
      created_at: response.user_message.created_at,
    }

    const idx = messages.value.findIndex(m => m.id === localMsg.id)
    if (idx !== -1) {
      messages.value.splice(idx, 1, serverUserMsg)
    }

    // 追加 AI 回复
    messages.value.push({
      id: response.ai_message.id,
      role: 'assistant',
      content: response.ai_message.content,
      status: 'sent',
      created_at: response.ai_message.created_at,
    })

    scrollToBottom()
  } catch (err) {
    if (!pageActive) return

    // 标记本地消息为失败，保留内容供重试
    const idx = messages.value.findIndex(m => m.id === localMsg.id)
    if (idx !== -1) {
      messages.value[idx] = { ...messages.value[idx], status: 'failed' }
    }

    const msg = err instanceof Error ? err.message : 'AI 服务暂时不可用，请稍后再试'
    uni.showToast({ title: msg, icon: 'none', duration: 3000 })
  } finally {
    if (pageActive) {
      isSending.value = false
    }
  }
}

// ========== 发送消息（含登录检查） ==========
function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isSending.value) return

  if (!userStore.isLoggedIn) {
    uni.showToast({ title: '请先登录', icon: 'none' })
    uni.navigateTo({ url: '/pages/auth/login' })
    return
  }

  doSend(text)
}

// ========== 重试失败消息 ==========
function retryMessage(msg: ChatMessage) {
  if (isSending.value || msg.status !== 'failed') return
  doSend(msg.content, String(msg.id))
}

// ========== 跳转登录 ==========
function goLogin() {
  uni.navigateTo({ url: '/pages/auth/login' })
}

// ========== Markdown 渲染 ==========

/** 将消息内容转为 HTML 字符串（仅 AI 消息使用 Markdown） */
function renderedContent(msg: ChatMessage): string {
  if (msg.role === 'assistant') {
    return markdownToHtml(msg.content)
  }
  // 用户消息保持纯文本，但转义 HTML
  return msg.content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}

// ========== 页面生命周期 ==========
onShow(() => {
  pageActive = true

  // 从隐藏状态恢复时，如果 isSending 卡住了，重置它
  // （请求层已处理了 response，这里做安全兜底）
  if (isSending.value) {
    const hasLocalSending = messages.value.some(
      m => m.isLocal && m.status === 'sending',
    )
    if (!hasLocalSending) {
      isSending.value = false
    }
  }

  if (userStore.isLoggedIn) {
    loadHistory()
  } else {
    ensureWelcomeMessage()
  }
})

onHide(() => {
  pageActive = false
})

onUnload(() => {
  pageActive = false
})
</script>

<template>
  <view class="chat-page">
    <NavBar title="AI 助手" />

    <!-- 顶部操作区 -->
    <view class="chat-top-actions">
      <button class="chat-plan-btn" @tap="goToGeneratePlan">
        <text class="chat-plan-icon">✈</text>
        <text>生成 AI 旅行计划</text>
      </button>
    </view>

    <!-- 消息列表 -->
    <scroll-view
      class="chat-list"
      scroll-y
      enhanced
      :show-scrollbar="false"
      :scroll-into-view="scrollIntoViewId"
    >
      <!-- 历史加载中 -->
      <view v-if="historyLoading" class="chat-status">
        <text>加载历史消息...</text>
      </view>

      <!-- 历史加载失败 -->
      <view v-if="historyError && !historyLoading" class="chat-status chat-status-error">
        <text>{{ historyError }}</text>
      </view>

      <!-- 消息列表 -->
      <view
        v-for="(msg, index) in messages"
        :key="msg.id"
        :id="'msg-' + index"
        class="chat-message"
        :class="{ 'chat-message-self': msg.role === 'user' }"
      >
        <view class="chat-bubble-row" :class="{ 'chat-bubble-row-self': msg.role === 'user' }">
          <view class="chat-bubble" :class="msg.role">
            <rich-text v-if="msg.role === 'assistant'" :nodes="renderedContent(msg)" />
            <text v-else>{{ msg.content }}</text>
          </view>

          <!-- 删除按钮（仅服务端消息） -->
          <view
            v-if="!isLocalId(msg.id) && msg.id !== 0"
            class="chat-delete-btn"
            :class="{ 'chat-delete-disabled': isDeleting(msg.id) }"
            @tap.stop="confirmDeleteSession(msg, $event)"
          >
            <text v-if="!isDeleting(msg.id)">🗑</text>
            <text v-else class="chat-deleting-spinner">⏳</text>
          </view>
        </view>

        <!-- 发送中指示 -->
        <view v-if="msg.status === 'sending'" class="chat-status-text">
          <text>发送中...</text>
        </view>

        <!-- 失败状态 + 重试入口 -->
        <view v-if="msg.status === 'failed'" class="chat-failed-row">
          <text class="chat-failed-text">发送失败</text>
          <text class="chat-retry-btn" @tap="retryMessage(msg)">重试</text>
        </view>
      </view>

      <!-- AI 回复中 -->
      <view v-if="isSending" class="chat-status">
        <text>AI 回复中...</text>
      </view>

      <!-- 空状态提示 -->
      <view v-if="messages.length <= 1 && !isSending && !historyLoading" class="chat-hint">
        <text>试着问我旅行相关的问题吧～</text>
      </view>

      <!-- 滚动锚点 -->
      <view id="chat-bottom-anchor" />
    </scroll-view>

    <!-- 输入区域 -->
    <view class="chat-input-bar safe-area-bottom">
      <template v-if="userStore.isLoggedIn">
        <input
          v-model="inputText"
          class="chat-input"
          placeholder="输入你的问题..."
          placeholder-style="color: #ccc;"
          confirm-type="send"
          :disabled="isSending"
          @confirm="sendMessage"
        />
        <button
          class="chat-send-btn"
          @tap="sendMessage"
          :disabled="!inputText.trim() || isSending"
        >
          {{ isSending ? '发送中' : '发送' }}
        </button>
      </template>

      <template v-else>
        <view class="chat-login-bar">
          <text class="chat-login-hint">登录后使用 AI 助手</text>
          <button class="chat-login-btn" @tap="goLogin">去登录</button>
        </view>
      </template>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.chat-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.chat-list {
  flex: 1;
  padding: 16rpx 24rpx;
  width: 100%;
  box-sizing: border-box;
}

.chat-message {
  margin-bottom: 24rpx;
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.chat-message-self {
  align-items: flex-end;
}

.chat-bubble {
  max-width: 80%;
  padding: 16rpx 24rpx;
  border-radius: 16rpx;
  font-size: 28rpx;
  line-height: 1.6;
  min-width: 0;
  box-sizing: border-box;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.chat-bubble.user {
  background: #4A90D9;
  color: #fff;
  border-bottom-right-radius: 4rpx;
  margin-right: 0;
}

.chat-bubble.assistant {
  background: #fff;
  color: #333;
  border-bottom-left-radius: 4rpx;
  max-width: 85%;
}

// ========== 顶部操作区 ==========
.chat-top-actions {
  padding: 16rpx 32rpx;
  background: #fff;
  border-bottom: 1rpx solid #eee;
}

.chat-plan-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  width: 100%;
  height: 80rpx;
  background: linear-gradient(135deg, #4A90D9, #357ABD);
  color: #fff;
  font-size: 30rpx;
  font-weight: 500;
  border-radius: 40rpx;
  border: none;
}

.chat-plan-btn::after {
  border: none;
}

.chat-plan-icon {
  font-size: 32rpx;
}

// ========== 消息行（气泡 + 删除按钮） ==========
.chat-bubble-row {
  display: flex;
  align-items: center;
  gap: 8rpx;
  max-width: 88%;
}

.chat-bubble-row-self {
  flex-direction: row-reverse;
  align-self: flex-end;
}

// ========== 删除按钮 ==========
.chat-delete-btn {
  flex-shrink: 0;
  width: 48rpx;
  height: 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: transparent;
  font-size: 28rpx;
  opacity: 0.4;
  transition: opacity 0.2s;
}

.chat-delete-btn:active {
  opacity: 0.8;
  background: rgba(255, 77, 79, 0.1);
}

.chat-delete-disabled {
  opacity: 0.2;
  pointer-events: none;
}

.chat-deleting-spinner {
  font-size: 24rpx;
  animation: chat-spin 1s linear infinite;
}

@keyframes chat-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// ========== 状态指示 ==========
.chat-status {
  text-align: center;
  padding: 24rpx;
}

.chat-status text {
  font-size: 24rpx;
  color: #aaa;
}

.chat-status-error text {
  color: #FF4D4F;
}

.chat-status-text {
  margin-top: 8rpx;
  text-align: right;
}

.chat-status-text text {
  font-size: 22rpx;
  color: #aaa;
}

// ========== 失败重试 ==========
.chat-failed-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-top: 8rpx;
}

.chat-failed-text {
  font-size: 22rpx;
  color: #FF4D4F;
}

.chat-retry-btn {
  font-size: 22rpx;
  color: #4A90D9;
  padding: 4rpx 12rpx;
}

// ========== 空状态 ==========
.chat-hint {
  text-align: center;
  padding-top: 200rpx;
  font-size: 28rpx;
  color: #bbb;
}

// ========== 输入区域 ==========
.chat-input-bar {
  display: flex;
  align-items: center;
  padding: 16rpx 24rpx;
  background: #fff;
  border-top: 1rpx solid #eee;
}

.chat-input {
  flex: 1;
  height: 72rpx;
  background: #f5f5f5;
  border-radius: 36rpx;
  padding: 0 24rpx;
  font-size: 28rpx;
}

.chat-send-btn {
  width: 120rpx;
  height: 72rpx;
  margin-left: 16rpx;
  background: #4A90D9;
  color: #fff;
  font-size: 28rpx;
  border-radius: 36rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-send-btn[disabled] {
  background: #ccc;
}

// ========== 未登录状态 ==========
.chat-login-bar {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24rpx;
}

.chat-login-hint {
  font-size: 28rpx;
  color: #999;
}

.chat-login-btn {
  background: #4A90D9;
  color: #fff;
  font-size: 26rpx;
  padding: 12rpx 32rpx;
  border-radius: 32rpx;
}
</style>
