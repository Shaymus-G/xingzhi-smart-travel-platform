<script setup lang="ts">
/**
 * Markdown 表格原生渲染组件
 *
 * 列宽策略：
 *   1 列  → 100% 自适应
 *   2 列  → 每列 50% 自适应
 *   3 列  → 优先 flex 自适应，含超长文本时启用滚动
 *   4+ 列 → 固定列宽 + 横向滚动 + 滑动提示
 *
 * H5 和 App 统一使用此组件（不再区分 rich-text table）。
 */

import { computed } from 'vue'

const props = defineProps<{
  headers: string[]
  alignments: Array<'left' | 'center' | 'right'>
  rows: string[][]
}>()

const columnCount = computed(() => props.headers.length)

/** 所有单元格去标签后的纯文本 */
const allPlainText = computed(() => {
  const texts: string[] = props.headers.map(stripHtml)
  for (const row of props.rows) {
    for (const cell of row) {
      texts.push(stripHtml(cell || ''))
    }
  }
  return texts
})

/** 是否存在超长单元格（纯文本 > 30 字符） */
const hasLongCell = computed(() =>
  allPlainText.value.some((t) => t.length > 30),
)

/** 是否启用横向滚动 */
const isScrollable = computed(() =>
  columnCount.value >= 4 ||
  (columnCount.value === 3 && hasLongCell.value),
)

/** 滚动模式下每列固定宽度 (rpx) */
const columnWidthRpx = computed(() => {
  if (columnCount.value <= 3) return 0
  if (columnCount.value === 4) return 190
  return 170
})

/** 表格 style 对象 */
const tableStyle = computed(() => {
  if (!isScrollable.value || columnWidthRpx.value <= 0) return {}
  return {
    width: `${columnCount.value * columnWidthRpx.value}rpx`,
    minWidth: `${columnCount.value * columnWidthRpx.value}rpx`,
  }
})

function cellStyle(): Record<string, string> {
  if (!isScrollable.value || columnWidthRpx.value <= 0) return {}
  return {
    width: `${columnWidthRpx.value}rpx`,
    minWidth: `${columnWidthRpx.value}rpx`,
    maxWidth: `${columnWidthRpx.value}rpx`,
  }
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]+>/g, '').trim()
}
</script>

<template>
  <view class="markdown-table-wrapper">
    <!-- 横向滑动提示 -->
    <view v-if="isScrollable" class="markdown-table-hint">
      <text>← 左右滑动查看完整表格 →</text>
    </view>

    <scroll-view
      class="markdown-table-scroll"
      :class="{ 'markdown-table-scroll--enabled': isScrollable }"
      :scroll-x="isScrollable"
      :show-scrollbar="false"
    >
      <view
        class="markdown-table-native"
        :class="{
          'markdown-table--fit': !isScrollable,
          'markdown-table--scroll': isScrollable,
        }"
        :style="tableStyle"
      >
        <!-- 表头 -->
        <view class="md-tr md-thead">
          <view
            v-for="(header, hi) in headers"
            :key="'h-' + hi"
            class="md-th"
            :class="'md-align-' + (alignments[hi] || 'left')"
            :style="isScrollable ? cellStyle() : {}"
          >
            <rich-text :nodes="header" />
          </view>
        </view>

        <!-- 数据行 -->
        <view
          v-for="(row, ri) in rows"
          :key="'r-' + ri"
          class="md-tr"
        >
          <view
            v-for="(cell, ci) in (row.length || headers.length)"
            :key="'c-' + ci"
            class="md-td"
            :class="'md-align-' + (alignments[ci] || 'left')"
            :style="isScrollable ? cellStyle() : {}"
          >
            <rich-text v-if="row[ci]" :nodes="row[ci]" />
          </view>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<style lang="scss" scoped>
// ===== Wrapper =====
.markdown-table-wrapper {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  margin: 12rpx 0;
}

// ===== Scroll hint =====
.markdown-table-hint {
  margin-bottom: 6rpx;
  text-align: right;

  text {
    font-size: 22rpx;
    color: #8a8f98;
  }
}

// ===== Scroll container =====
.markdown-table-scroll {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.markdown-table-scroll--enabled {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

// ===== Table body =====
.markdown-table-native {
  border: 1px solid #e5e7eb;
  border-radius: 10rpx;
  overflow: hidden;
}

// Fit mode (1-3 cols, no scroll)
.markdown-table--fit {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

// Scroll mode (4+ cols)
.markdown-table--scroll {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

// ===== Table row =====
.md-tr {
  display: flex;
  flex-direction: row;
  border-bottom: 1px solid #e5e7eb;
  width: 100%;
  min-width: 0;

  &:last-child {
    border-bottom: none;
  }
}

.markdown-table--scroll .md-tr {
  flex-wrap: nowrap;
}

.md-thead {
  background: #f6f7f9;
}

// ===== Cells =====
.md-th {
  font-weight: 600;
  font-size: 24rpx;
  color: #333;
  padding: 14rpx 16rpx;
  border-right: 1px solid #e5e7eb;
  box-sizing: border-box;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  min-width: 0;

  &:last-child {
    border-right: none;
  }
}

.md-td {
  font-size: 24rpx;
  color: #333;
  padding: 14rpx 16rpx;
  border-right: 1px solid #e5e7eb;
  box-sizing: border-box;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  min-width: 0;

  &:last-child {
    border-right: none;
  }
}

// Fit mode: flex cells
.markdown-table--fit .md-th,
.markdown-table--fit .md-td {
  flex: 1;
  min-width: 0;
}

// Scroll mode: fixed-width cells
.markdown-table--scroll .md-th,
.markdown-table--scroll .md-td {
  flex: none;
  white-space: normal;
}

// ===== Alignment =====
.md-align-left {
  text-align: left;
  justify-content: flex-start;
}

.md-align-center {
  text-align: center;
  justify-content: center;
}

.md-align-right {
  text-align: right;
  justify-content: flex-end;
}

// ===== Rich-text internals =====
.md-th :deep(rich-text),
.md-td :deep(rich-text) {
  word-break: break-word;
  overflow-wrap: anywhere;
  width: 100%;
}
</style>
