<script setup lang="ts">
/**
 * 安全图片组件 — 统一处理：
 *  - URL 解析（resolveImageUrl）
 *  - props 变化时重新解析
 *  - 加载失败 fallback
 *  - 防止 fallback 循环
 *  - H5 / App 跨端兼容
 *
 * 用法：
 *   <SafeImage :src="item.image_url" class="my-img" mode="aspectFill" />
 */
import { ref, watch } from 'vue'
import { resolveImageUrl, DEFAULT_IMAGE } from '@/utils/image'

interface Props {
  /** 原始图片字段值（可能为空、相对路径、完整 URL 等） */
  src?: string | null
  /** 图片模式，同 uni-app <image> mode */
  mode?: string
  /** 自定义 fallback 图，不传使用项目默认图 */
  fallback?: string
}

const props = withDefaults(defineProps<Props>(), {
  src: '',
  mode: 'aspectFill',
  fallback: '',
})

const currentSrc = ref('')
const defaultImage = props.fallback || DEFAULT_IMAGE

/** 更新当前显示 URL */
function updateSrc() {
  currentSrc.value = resolveImageUrl(props.src, defaultImage)
}

// 初始化
updateSrc()

// 监听 props 变化（v-for 复用、分页刷新时重新解析）
watch(
  () => [props.src, props.fallback],
  () => {
    updateSrc()
  },
)

/** 图片加载失败时回退到默认图 */
function handleError() {
  if (currentSrc.value !== defaultImage) {
    currentSrc.value = defaultImage
  }
  // 如果已经是默认图还失败，不再处理（防止循环）
}
</script>

<template>
  <image
    class="safe-image"
    :src="currentSrc"
    :mode="mode"
    @error="handleError"
  />
</template>

<style scoped>
.safe-image {
  /* 由父组件通过 class 控制尺寸 */
  background: #f0f0f0;
}
</style>
