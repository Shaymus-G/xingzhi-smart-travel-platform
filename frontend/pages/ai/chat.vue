<script setup lang="ts">
/**
 * AI 对话页面 — 接入后端 DeepSeek 真实接口
 */
import { ref, nextTick } from 'vue'
import NavBar from '@/components/NavBar.vue'
import { sendChatMessage } from '@/api/ai'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
}

const messages = ref<ChatMessage[]>([
  { id: 0, role: 'assistant', content: '你好！我是行知 AI 旅行助手，有什么可以帮助你的吗？' },
])
const inputText = ref('')
const isSending = ref(false)
const currentSessionId = ref<number | undefined>(undefined)

function scrollToBottom() {
  nextTick(() => {
    // uni-app scroll-view 通过 :scroll-into-view 自动滚动
  })
}

function goToGeneratePlan() {
  uni.navigateTo({ url: '/pages/plan/generate' })
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isSending.value) return

  // 本地添加用户消息
  const userMsg: ChatMessage = { id: Date.now(), role: 'user', content: text }
  messages.value.push(userMsg)
  inputText.value = ''
  scrollToBottom()

  isSending.value = true

  try {
    const response = await sendChatMessage({
      message: text,
      session_id: currentSessionId.value,
    })

    // 保存 session_id 用于后续对话
    currentSessionId.value = response.session_id

    // 添加 AI 回复
    messages.value.push({
      id: Date.now(),
      role: 'assistant',
      content: response.ai_message.content,
    })
    scrollToBottom()
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'AI 服务暂时不可用，请稍后再试'
    uni.showToast({ title: msg, icon: 'none', duration: 3000 })
  } finally {
    isSending.value = false
  }
}
</script>

<template>
  <view class="chat-page">
    <NavBar title="AI 助手" />

    <!-- 计划生成入口 -->
    <view class="plan-entry" @tap="goToGeneratePlan">
      <text class="plan-entry-icon">📋</text>
      <text>生成完整行程</text>
    </view>

    <!-- 消息列表 -->
    <scroll-view
      ref="scrollViewRef"
      class="chat-list"
      scroll-y
      enhanced
      :scroll-into-view="'msg-' + (messages.length - 1)"
    >
      <view
        v-for="(msg, index) in messages"
        :key="msg.id"
        :id="'msg-' + index"
        class="chat-message"
        :class="{ 'chat-message-self': msg.role === 'user' }"
      >
        <view class="chat-bubble" :class="msg.role">
          <text>{{ msg.content }}</text>
        </view>
      </view>

      <!-- 加载状态 -->
      <view v-if="isSending" class="chat-loading">
        <text>AI 回复中...</text>
      </view>

      <!-- 空状态提示 -->
      <view v-if="messages.length <= 1 && !isSending" class="chat-hint">
        <text>试着问我旅行相关的问题吧～</text>
      </view>
    </scroll-view>

    <!-- 输入区域 -->
    <view class="chat-input-bar safe-area-bottom">
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

.plan-entry {
  margin: 12rpx 32rpx;
  padding: 16rpx 24rpx;
  background: #fff;
  border: 2rpx solid #4A90D9;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  font-size: 26rpx;
  color: #4A90D9;
  font-weight: 600;
}

.plan-entry-icon {
  font-size: 32rpx;
}

.chat-list {
  flex: 1;
  padding: 16rpx 32rpx;
}

.chat-message {
  margin-bottom: 24rpx;
  display: flex;
}

.chat-message-self {
  justify-content: flex-end;
}

.chat-bubble {
  max-width: 80%;
  padding: 16rpx 24rpx;
  border-radius: 16rpx;
  font-size: 28rpx;
  line-height: 1.6;
}

.chat-bubble.user {
  background: #4A90D9;
  color: #fff;
  border-bottom-right-radius: 4rpx;
}

.chat-bubble.assistant {
  background: #fff;
  color: #333;
  border-bottom-left-radius: 4rpx;
}

.chat-loading {
  text-align: center;
  padding: 24rpx;
}

.chat-loading text {
  font-size: 24rpx;
  color: #aaa;
}

.chat-hint {
  text-align: center;
  padding-top: 200rpx;
  font-size: 28rpx;
  color: #bbb;
}

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
</style>
