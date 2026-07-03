import { describe, it, expect } from 'vitest'
import { cn } from '@/lib/utils'

describe('lib/utils', () => {
  describe('cn', () => {
    it('should merge class names', () => {
      expect(cn('foo', 'bar')).toBe('foo bar')
    })

    it('should handle conditional classes', () => {
      expect(cn('base', false && 'hidden', 'visible')).toBe('base visible')
    })

    it('should handle undefined and null', () => {
      expect(cn('base', undefined, null, 'end')).toBe('base end')
    })

    it('should merge tailwind conflicts (twMerge)', () => {
      // twMerge should resolve conflicting tailwind classes
      expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4')
    })

    it('should handle empty input', () => {
      expect(cn()).toBe('')
    })

    it('should handle array input via clsx', () => {
      expect(cn(['foo', 'bar'])).toBe('foo bar')
    })

    it('should handle object input via clsx', () => {
      expect(cn({ foo: true, bar: false, baz: true })).toBe('foo baz')
    })
  })
})
