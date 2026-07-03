import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useWardrobeStore } from '@/store/wardrobe'

vi.mock('@/lib/api', () => ({
  getWardrobeItems: vi.fn(),
  addWardrobeItem: vi.fn(),
  deleteWardrobeItem: vi.fn(),
  updateWardrobeItem: vi.fn(),
  previewTagging: vi.fn(),
}))

import {
  getWardrobeItems,
  addWardrobeItem,
  deleteWardrobeItem,
  updateWardrobeItem,
  previewTagging,
} from '@/lib/api'

const mockItem = {
  id: 1,
  user_id: 1,
  name: '白色T恤',
  primary_element: '金',
  is_custom: false,
  is_active: true,
  wear_count: 0,
  is_favorite: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

describe('useWardrobeStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useWardrobeStore.setState({
      items: [],
      total: 0,
      elementStats: {},
      isLoading: false,
      error: null,
      taggingPreview: null,
      isTaggingLoading: false,
    })
  })

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const state = useWardrobeStore.getState()
      expect(state.items).toEqual([])
      expect(state.total).toBe(0)
      expect(state.elementStats).toEqual({})
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
      expect(state.taggingPreview).toBeNull()
      expect(state.isTaggingLoading).toBe(false)
    })
  })

  describe('fetchItems', () => {
    it('should fetch items successfully', async () => {
      vi.mocked(getWardrobeItems).mockResolvedValue({
        items: [mockItem],
        total: 1,
        element_stats: { '金': 1 },
      })

      await useWardrobeStore.getState().fetchItems({ category: '上衣' })

      expect(getWardrobeItems).toHaveBeenCalledWith({ category: '上衣', limit: 100 })
      const state = useWardrobeStore.getState()
      expect(state.items).toEqual([mockItem])
      expect(state.total).toBe(1)
      expect(state.elementStats).toEqual({ '金': 1 })
      expect(state.isLoading).toBe(false)
    })

    it('should fetch items without filters', async () => {
      vi.mocked(getWardrobeItems).mockResolvedValue({
        items: [],
        total: 0,
        element_stats: {},
      })

      await useWardrobeStore.getState().fetchItems()

      expect(getWardrobeItems).toHaveBeenCalledWith({ limit: 100 })
    })

    it('should set error on fetch failure', async () => {
      vi.mocked(getWardrobeItems).mockRejectedValue(new Error('Network error'))

      await useWardrobeStore.getState().fetchItems()

      const state = useWardrobeStore.getState()
      expect(state.error).toBe('Network error')
      expect(state.isLoading).toBe(false)
    })

    it('should set generic error for non-Error throws', async () => {
      vi.mocked(getWardrobeItems).mockRejectedValue('fail')

      await useWardrobeStore.getState().fetchItems()

      expect(useWardrobeStore.getState().error).toBe('获取衣橱列表失败')
    })
  })

  describe('addItem', () => {
    it('should add item successfully', async () => {
      vi.mocked(addWardrobeItem).mockResolvedValue(mockItem)

      const result = await useWardrobeStore.getState().addItem({
        name: '白色T恤',
        primary_element: '金',
      })

      expect(addWardrobeItem).toHaveBeenCalledWith({ name: '白色T恤', primary_element: '金' })
      expect(result).toEqual(mockItem)
      const state = useWardrobeStore.getState()
      expect(state.items).toEqual([mockItem])
      expect(state.total).toBe(1)
      expect(state.isLoading).toBe(false)
    })

    it('should prepend new item to existing items', async () => {
      useWardrobeStore.setState({ items: [mockItem], total: 1 })
      const newItem = { ...mockItem, id: 2, name: '黑色裤子' }
      vi.mocked(addWardrobeItem).mockResolvedValue(newItem)

      await useWardrobeStore.getState().addItem({ name: '黑色裤子' })

      const state = useWardrobeStore.getState()
      expect(state.items).toHaveLength(2)
      expect(state.items[0]).toEqual(newItem)
      expect(state.items[1]).toEqual(mockItem)
      expect(state.total).toBe(2)
    })

    it('should set error on add failure', async () => {
      vi.mocked(addWardrobeItem).mockRejectedValue(new Error('添加失败'))

      await expect(useWardrobeStore.getState().addItem({ name: 'test' })).rejects.toThrow('添加失败')

      const state = useWardrobeStore.getState()
      expect(state.error).toBe('添加失败')
      expect(state.isLoading).toBe(false)
    })
  })

  describe('updateItem', () => {
    it('should update item successfully', async () => {
      useWardrobeStore.setState({ items: [mockItem], total: 1 })
      const updatedItem = { ...mockItem, name: 'Updated Name' }
      vi.mocked(updateWardrobeItem).mockResolvedValue(updatedItem)

      await useWardrobeStore.getState().updateItem(1, { name: 'Updated Name' })

      expect(updateWardrobeItem).toHaveBeenCalledWith(1, { name: 'Updated Name' })
      const state = useWardrobeStore.getState()
      expect(state.items[0]).toEqual(updatedItem)
      expect(state.isLoading).toBe(false)
    })

    it('should set error on update failure', async () => {
      vi.mocked(updateWardrobeItem).mockRejectedValue(new Error('更新失败'))

      await expect(useWardrobeStore.getState().updateItem(1, {})).rejects.toThrow('更新失败')

      expect(useWardrobeStore.getState().error).toBe('更新失败')
    })
  })

  describe('deleteItem', () => {
    it('should delete item successfully', async () => {
      useWardrobeStore.setState({ items: [mockItem, { ...mockItem, id: 2 }], total: 2 })
      vi.mocked(deleteWardrobeItem).mockResolvedValue(undefined)

      await useWardrobeStore.getState().deleteItem(1)

      expect(deleteWardrobeItem).toHaveBeenCalledWith(1)
      const state = useWardrobeStore.getState()
      expect(state.items).toHaveLength(1)
      expect(state.items[0].id).toBe(2)
      expect(state.total).toBe(1)
      expect(state.isLoading).toBe(false)
    })

    it('should set error on delete failure', async () => {
      vi.mocked(deleteWardrobeItem).mockRejectedValue(new Error('删除失败'))

      await expect(useWardrobeStore.getState().deleteItem(1)).rejects.toThrow('删除失败')

      expect(useWardrobeStore.getState().error).toBe('删除失败')
    })
  })

  describe('clearError', () => {
    it('should clear error', () => {
      useWardrobeStore.setState({ error: 'some error' })
      useWardrobeStore.getState().clearError()
      expect(useWardrobeStore.getState().error).toBeNull()
    })
  })

  describe('fetchTaggingPreview', () => {
    it('should fetch tagging preview successfully', async () => {
      const mockResult = {
        primary_element: '木',
        color: 'green',
        season: ['spring'],
        tags: ['casual'],
        confidence: 0.9,
      }
      vi.mocked(previewTagging).mockResolvedValue(mockResult)

      await useWardrobeStore.getState().fetchTaggingPreview('绿色T恤')

      expect(previewTagging).toHaveBeenCalledWith('绿色T恤')
      const state = useWardrobeStore.getState()
      expect(state.taggingPreview).toEqual(mockResult)
      expect(state.isTaggingLoading).toBe(false)
    })

    it('should set error on tagging failure', async () => {
      vi.mocked(previewTagging).mockRejectedValue(new Error('AI打标失败'))

      await useWardrobeStore.getState().fetchTaggingPreview('test')

      const state = useWardrobeStore.getState()
      expect(state.error).toBe('AI打标失败')
      expect(state.isTaggingLoading).toBe(false)
    })
  })

  describe('clearTaggingPreview', () => {
    it('should clear tagging preview', () => {
      useWardrobeStore.setState({ taggingPreview: { primary_element: '木' } as any })
      useWardrobeStore.getState().clearTaggingPreview()
      expect(useWardrobeStore.getState().taggingPreview).toBeNull()
    })
  })
})
