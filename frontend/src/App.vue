<script setup lang="ts">
import { onLaunch, onShow, onHide } from '@dcloudio/uni-app'

onLaunch(() => {
  console.log('[XingZhi] App Launch')
})

onShow(() => {
  console.log('[XingZhi] App Show')
})

onHide(() => {
  console.log('[XingZhi] App Hide')
})
</script>

<style lang="scss">
/* 全局样式 */
@use './styles/common.scss' as *;

/* 每个页面公共css */
page {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 28rpx;
  color: #333;
  background-color: #f5f5f5;
  box-sizing: border-box;
}

/* ==================== AI Markdown 渲染样式 ==================== */

/* rich-text 内渲染的 markdown 内容 */
.chat-bubble.assistant rich-text {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

/* 标题 */
.chat-bubble.assistant h1,
.chat-bubble.assistant h2,
.chat-bubble.assistant h3 {
  font-weight: 700;
  margin: 8rpx 0;
  line-height: 1.4;
  color: #333;
}

.chat-bubble.assistant h1 { font-size: 32rpx; }
.chat-bubble.assistant h2 { font-size: 30rpx; }
.chat-bubble.assistant h3 { font-size: 28rpx; }

/* 段落 */
.chat-bubble.assistant p {
  margin: 6rpx 0;
  line-height: 1.7;
  color: #333;
  word-break: break-word;
  overflow-wrap: anywhere;
}

/* 粗体 / 斜体 */
.chat-bubble.assistant strong {
  font-weight: 700;
}

.chat-bubble.assistant em {
  font-style: italic;
}

/* 行内代码 */
.chat-bubble.assistant code {
  background: #f0f0f0;
  padding: 2rpx 8rpx;
  border-radius: 6rpx;
  font-family: 'Courier New', Courier, monospace;
  font-size: 24rpx;
  color: #d93025;
  word-break: break-all;
}

/* 代码块 */
.chat-bubble.assistant pre {
  background: #2d2d2d;
  color: #e0e0e0;
  padding: 16rpx;
  border-radius: 12rpx;
  margin: 12rpx 0;
  overflow-x: auto;
  max-width: 100%;
  box-sizing: border-box;
  white-space: pre-wrap;
  word-break: break-all;
}

.chat-bubble.assistant pre code {
  background: transparent;
  color: inherit;
  padding: 0;
  font-size: 24rpx;
  border-radius: 0;
}

/* 列表 */
.chat-bubble.assistant ul,
.chat-bubble.assistant ol {
  padding-left: 0;
  margin: 12rpx 0;
  box-sizing: border-box;
}

/* 嵌套列表通用 */
.chat-bubble.assistant .md-list {
  margin: 6rpx 0;
  padding-left: 36rpx;
  box-sizing: border-box;
}

/* 一级：实心圆 */
.chat-bubble.assistant .md-list-level-1 {
  list-style-type: disc;
}

/* 二级：空心圆 */
.chat-bubble.assistant .md-list-level-2 {
  list-style-type: circle;
  margin-top: 4rpx;
  padding-left: 32rpx;
}

/* 三级及以后：方块 */
.chat-bubble.assistant .md-list-level-3,
.chat-bubble.assistant .md-list-level-4,
.chat-bubble.assistant .md-list-level-5 {
  list-style-type: square;
  margin-top: 4rpx;
  padding-left: 28rpx;
}

.chat-bubble.assistant li {
  margin: 6rpx 0;
  line-height: 1.65;
  color: #333;
}

/* 引用 */
.chat-bubble.assistant blockquote {
  border-left: 6rpx solid #4A90D9;
  padding: 8rpx 16rpx;
  margin: 12rpx 0;
  background: #f5f7fa;
  border-radius: 0 8rpx 8rpx 0;
}

.chat-bubble.assistant blockquote p {
  margin: 0;
  color: #555;
}

/* 链接 */
.chat-bubble.assistant a {
  color: #4A90D9;
  text-decoration: underline;
  word-break: break-all;
}

/* 水平线 */
.chat-bubble.assistant hr {
  border: none;
  border-top: 1rpx solid #e0e0e0;
  margin: 16rpx 0;
}

/* 图片 */
.chat-bubble.assistant img {
  max-width: 100%;
  height: auto;
}
</style>
