import { describe, it, expect } from 'vitest'
import { getImageUrl } from '@/lib/image'

describe('lib/image', () => {
  describe('getImageUrl', () => {
    it('should return undefined for null input', () => {
      expect(getImageUrl(null)).toBeUndefined()
    })

    it('should return undefined for undefined input', () => {
      expect(getImageUrl(undefined)).toBeUndefined()
    })

    it('should return undefined for empty string', () => {
      expect(getImageUrl('')).toBeUndefined()
    })

    it('should return http URL as-is', () => {
      const url = 'http://example.com/image.jpg'
      expect(getImageUrl(url)).toBe(url)
    })

    it('should return https URL as-is', () => {
      const url = 'https://example.com/image.jpg'
      expect(getImageUrl(url)).toBe(url)
    })

    it('should prefix /images/ with R2 base URL', () => {
      const url = '/images/seed/item001.jpg'
      const result = getImageUrl(url)
      expect(result).toContain('/images/seed/item001.jpg')
      expect(result).toMatch(/^https?:\/\//)
    })

    it('should return /uploads/ path as encoded relative path', () => {
      const url = '/uploads/wardrobe/test image.jpg'
      const result = getImageUrl(url)
      expect(result).toBeDefined()
      expect(result).toContain('/uploads/')
    })

    it('should handle already-encoded /uploads/ URLs without double encoding', () => {
      const url = '/uploads/wardrobe/test%20image.jpg'
      const result = getImageUrl(url)
      expect(result).toBe('/uploads/wardrobe/test%20image.jpg')
    })

    it('should prefix other relative paths with API base URL', () => {
      const url = '/api/v1/some/path'
      const result = getImageUrl(url)
      expect(result).toContain('/api/v1/some/path')
    })
  })
})
