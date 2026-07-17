<script setup lang="ts">
/**
 * AI 对话页面（骨架）
 * 后续接入 sendChatMessage({ message }) 接口
 */
import { ref, nextTick } from 'vue'
import NavBar from '@/components/NavBar.vue'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
}

const messages = ref<ChatMessage[]>([
  { id: 0, role: 'assistant', content: '你好！我是行知 AI 旅行助手，有什么可以帮助你的吗？' },
])
const inputText = ref('')
const scrollViewRef = ref<any>(null)

function scrollToBottom() {
  nextTick(() => {
    // uni-app scroll-view 自动滚动
  })
}

function sendMessage() {
  const text = inputText.value.trim()
  if (!text) return

  // 添加用户消息
  messages.value.push({ id: Date.now(), role: 'user', content: text })
  inputText.value = ''
  scrollToBottom()

  // 骨架：模拟 AI 回复
  setTimeout(() => {
    messages.value.push({
      id: Date.now(),
      role: 'assistant',
      content: `[骨架回复] 收到你的消息："${text}"。AI 对话功能将在后续接入 DeepSeek 后端接口后启用。`,
    })
    scrollToBottom()
  }, 800)
}
</script>

<template>
  <view class="chat-page">
    <NavBar title="AI 助手" />

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

      <!-- 空状态提示 -->
      <view v-if="messages.length <= 1" class="chat-hint">
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
        @confirm="sendMessage"
      />
      <button class="chat-send-btn" @tap="sendMessage" :disabled="!inputText.trim()">
        发送
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
