/**
 * 全局应用状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  /** 全局加载状态 */
  const isLoading = ref(false)

  /** 当前选中的城市 ID */
  const currentCityId = ref<number | null>(null)

  /** 设置加载状态 */
  function setLoading(loading: boolean) {
    isLoading.value = loading
  }

  /** 设置当前城市 */
  function setCurrentCity(cityId: number) {
    currentCityId.value = cityId
  }

  return {
    isLoading,
    currentCityId,
    setLoading,
    setCurrentCity,
  }
})
