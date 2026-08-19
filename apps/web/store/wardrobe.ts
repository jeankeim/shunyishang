/**
 * 衣橱状态管理
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import {
  WardrobeItem,
  WardrobeListResponse,
  AITaggingResult,
  getWardrobeItems,
  addWardrobeItem,
  deleteWardrobeItem,
  updateWardrobeItem,
  UpdateWardrobeItemRequest,
  previewTagging,
  AddWardrobeItemRequest,
  batchAddWardrobeItems,
  BatchAddItemRequest,
  BatchAddResponse,
} from '@/lib/api'

interface WardrobeState {
  // 衣橱数据
  items: WardrobeItem[]
  total: number
  elementStats: Record<string, number>

  // 加载状态
  isLoading: boolean
  error: string | null

  // AI 打标
  taggingPreview: AITaggingResult | null
  isTaggingLoading: boolean

  // 操作方法
  fetchItems: (filters?: { category?: string; element?: string }) => Promise<void>
  addItem: (data: AddWardrobeItemRequest) => Promise<WardrobeItem>
  addItems: (items: BatchAddItemRequest[]) => Promise<BatchAddResponse>
  updateItem: (itemId: number, data: UpdateWardrobeItemRequest) => Promise<void>
  deleteItem: (itemId: number) => Promise<void>
  clearError: () => void

  // AI 打标
  fetchTaggingPreview: (description: string, imageUrl?: string) => Promise<void>
  clearTaggingPreview: () => void
}

export const useWardrobeStore = create<WardrobeState>()(
  persist(
    (set) => ({
      items: [],
      total: 0,
      elementStats: {},
      isLoading: false,
      error: null,
      taggingPreview: null,
      isTaggingLoading: false,

      fetchItems: async (filters?: { category?: string; element?: string }) => {
        set({ isLoading: true, error: null })
        try {
          const response: WardrobeListResponse = await getWardrobeItems({
            ...filters,
            limit: 100,
          })
          set({
            items: response.items,
            total: response.total,
            elementStats: response.element_stats,
            isLoading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '获取衣橱列表失败',
            isLoading: false,
          })
        }
      },

      addItem: async (data: any) => {
        set({ isLoading: true, error: null })
        try {
          const newItem = await addWardrobeItem(data)
          set((state) => ({
            items: [newItem, ...state.items],
            total: state.total + 1,
            isLoading: false,
          }))
          return newItem
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '添加衣物失败',
            isLoading: false,
          })
          throw error
        }
      },

      addItems: async (data: BatchAddItemRequest[]) => {
        set({ isLoading: true, error: null })
        try {
          const response = await batchAddWardrobeItems(data)
          set((state) => ({
            items: [...response.created, ...state.items],
            total: state.total + response.created.length,
            isLoading: false,
          }))
          return response
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '批量入库失败',
            isLoading: false,
          })
          throw error
        }
      },

      updateItem: async (itemId: number, data: UpdateWardrobeItemRequest) => {
        set({ isLoading: true, error: null })
        try {
          const updatedItem = await updateWardrobeItem(itemId, data)
          set((state) => ({
            items: state.items.map((item) =>
              item.id === itemId ? updatedItem : item
            ),
            isLoading: false,
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '更新衣物失败',
            isLoading: false,
          })
          throw error
        }
      },

      deleteItem: async (itemId: number) => {
        set({ isLoading: true, error: null })
        try {
          await deleteWardrobeItem(itemId)
          set((state) => ({
            items: state.items.filter((item) => item.id !== itemId),
            total: state.total - 1,
            isLoading: false,
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '删除衣物失败',
            isLoading: false,
          })
          throw error
        }
      },

      clearError: () => set({ error: null }),

      // AI 打标预览
      fetchTaggingPreview: async (description: string, imageUrl?: string) => {
        set({ isTaggingLoading: true, error: null })
        try {
          const result = await previewTagging(description, imageUrl)
          set({ taggingPreview: result, isTaggingLoading: false })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'AI 打标失败',
            isTaggingLoading: false,
          })
        }
      },

      clearTaggingPreview: () => set({ taggingPreview: null }),
    }),
    {
      name: 'wardrobe-storage',
      skipHydration: true,
      partialize: (state) => ({
        // 不持久化敏感数据
      }),
    }
  )
)
