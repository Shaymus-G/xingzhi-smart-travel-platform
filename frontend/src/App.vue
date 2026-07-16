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
@use '@/styles/common.scss' as *;

/* 每个页面公共css */
page {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 28rpx;
  color: #333;
  background-color: #f5f5f5;
  box-sizing: border-box;
}
</style>
