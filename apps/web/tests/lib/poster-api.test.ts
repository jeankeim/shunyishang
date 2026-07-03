import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockFetch = vi.fn()
global.fetch = mockFetch as any

// Mock URL.createObjectURL and URL.revokeObjectURL
global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
global.URL.revokeObjectURL = vi.fn()

import {
  generateAndDownloadPoster,
  generatePosterBase64,
  base64ToBlob,
  sharePosterWithBase64,
  PosterGenerateParams,
} from '@/lib/poster-api'

const mockParams: PosterGenerateParams = {
  layout: 'simple',
  title: 'Test Poster',
  items: [{ name: 'T-shirt', primary_element: '木' }],
  xiyong_elements: ['木'],
  theme: 'wood',
  quote: 'Test quote',
  signature: 'Test signature',
  scene: 'office',
}

describe('lib/poster-api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('generateAndDownloadPoster', () => {
    it('should download poster on success', async () => {
      const mockBlob = new Blob(['test'], { type: 'image/png' })
      mockFetch.mockReturnValue({
        ok: true,
        blob: vi.fn().mockResolvedValue(mockBlob),
      })

      await generateAndDownloadPoster(mockParams)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/poster/generate'),
        expect.objectContaining({ method: 'POST' })
      )
      expect(URL.createObjectURL).toHaveBeenCalledWith(mockBlob)
      expect(URL.revokeObjectURL).toHaveBeenCalled()
    })

    it('should throw on failure', async () => {
      mockFetch.mockReturnValue({
        ok: false,
        statusText: 'Internal Server Error',
      })

      await expect(generateAndDownloadPoster(mockParams)).rejects.toThrow('海报生成失败')
    })
  })

  describe('generatePosterBase64', () => {
    it('should return base64 data on success', async () => {
      const mockData = { image: 'base64data', filename: 'test.png', size: 1024 }
      mockFetch.mockReturnValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockData),
      })

      const result = await generatePosterBase64(mockParams)

      expect(result).toEqual(mockData)
    })

    it('should throw on failure', async () => {
      mockFetch.mockReturnValue({
        ok: false,
        statusText: 'Bad Request',
      })

      await expect(generatePosterBase64(mockParams)).rejects.toThrow('海报生成失败')
    })
  })

  describe('base64ToBlob', () => {
    it('should convert base64 string to Blob', () => {
      // Use a simple base64 string
      const base64 = btoa('Hello World')
      const blob = base64ToBlob(base64, 'image/png')

      expect(blob).toBeInstanceOf(Blob)
      expect(blob.type).toBe('image/png')
    })

    it('should use default mime type', () => {
      const base64 = btoa('Test')
      const blob = base64ToBlob(base64)

      expect(blob.type).toBe('image/png')
    })

    it('should handle long base64 strings (multiple chunks)', () => {
      // Create a string longer than 512 characters
      const longString = 'A'.repeat(600)
      const base64 = btoa(longString)
      const blob = base64ToBlob(base64)

      expect(blob).toBeInstanceOf(Blob)
      expect(blob.size).toBeGreaterThan(0)
    })
  })

  describe('sharePosterWithBase64', () => {
    it('should use Web Share API when available', async () => {
      const mockData = { image: btoa('test'), filename: 'test.png', size: 100 }
      mockFetch.mockReturnValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockData),
      })

      // Mock navigator.share and navigator.canShare
      const shareMock = vi.fn().mockResolvedValue(undefined)
      const canShareMock = vi.fn().mockReturnValue(true)
      Object.defineProperty(navigator, 'share', { value: shareMock, writable: true, configurable: true })
      Object.defineProperty(navigator, 'canShare', { value: canShareMock, writable: true, configurable: true })

      await sharePosterWithBase64(mockParams)

      expect(shareMock).toHaveBeenCalled()
    })

    it('should fall back to download when Web Share API is not available', async () => {
      const mockData = { image: btoa('test'), filename: 'test.png', size: 100 }
      mockFetch.mockReturnValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockData),
      })

      // Remove navigator.share
      Object.defineProperty(navigator, 'share', { value: undefined, writable: true, configurable: true })
      Object.defineProperty(navigator, 'canShare', { value: undefined, writable: true, configurable: true })

      await sharePosterWithBase64(mockParams)

      expect(URL.createObjectURL).toHaveBeenCalled()
      expect(URL.revokeObjectURL).toHaveBeenCalled()
    })
  })
})
