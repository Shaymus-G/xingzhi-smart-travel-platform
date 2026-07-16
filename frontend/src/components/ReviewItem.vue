<script setup lang="ts">
/**
 * 评论条目组件
 */
import { computed } from 'vue'
import type { Review } from '@/types/social'

interface Props {
  review: Review
  showActions?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showActions: false,
})

const emit = defineEmits<{
  delete: [id: number]
  edit: [review: Review]
}>()

/** 用户名 */
const username = computed(() => {
  return props.review.user?.username || '匿名用户'
})

/** 格式化评分 */
const scoreDisplay = computed(() => {
  const s = Number(props.review.score)
  if (isNaN(s)) return ''
  return '★ ' + s.toFixed(1)
})

/** 格式化时间 */
const timeDisplay = computed(() => {
  const t = props.review.created_at
  if (!t) return ''
  // 简单截取前 16 位作为日期时间显示: "2026-07-17T12:00"
  return t.replace('T', ' ').slice(0, 16)
})
</script>

<template>
  <view class="review-item">
    <view class="review-header">
      <view class="review-user">
        <text class="review-username">{{ username }}</text>
        <text v-if="scoreDisplay" class="review-score">{{ scoreDisplay }}</text>
      </view>
      <text v-if="timeDisplay" class="review-time">{{ timeDisplay }}</text>
    </view>
    <text class="review-content">{{ review.content }}</text>
    <view v-if="showActions" class="review-actions">
      <text class="review-action" @tap="emit('edit', review)">编辑</text>
      <text class="review-action review-action-danger" @tap="emit('delete', review.id)">删除</text>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.review-item {
  padding: 24rpx 0;
  border-bottom: 1rpx solid #f0f0f0;
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12rpx;
}

.review-user {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.review-username {
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
}

.review-score {
  font-size: 24rpx;
  color: #FF8C00;
}

.review-time {
  font-size: 22rpx;
  color: #ccc;
}

.review-content {
  font-size: 28rpx;
  color: #666;
  line-height: 1.6;
}

.review-actions {
  display: flex;
  gap: 32rpx;
  margin-top: 16rpx;
}

.review-action {
  font-size: 24rpx;
  color: #4A90D9;
}

.review-action-danger {
  color: #FF4D4F;
}
</style>
