import { describe, it, expect } from 'vitest'
import {
  WUXING_ELEMENTS,
  WUXING_CONFIG,
  getWuxingConfig,
  TIANGAN_WUXING,
  DIZHI_WUXING,
  WuxingElement,
} from '@/lib/wuxing-config'

describe('lib/wuxing-config', () => {
  describe('WUXING_ELEMENTS', () => {
    it('should contain all five elements', () => {
      expect(WUXING_ELEMENTS).toEqual(['金', '木', '水', '火', '土'])
    })
  })

  describe('WUXING_CONFIG', () => {
    it('should have config for all five elements', () => {
      for (const element of WUXING_ELEMENTS) {
        expect(WUXING_CONFIG[element]).toBeDefined()
        expect(WUXING_CONFIG[element].element).toBe(element)
        expect(WUXING_CONFIG[element].emoji).toBeDefined()
        expect(WUXING_CONFIG[element].color).toBeDefined()
        expect(WUXING_CONFIG[element].bgClass).toBeDefined()
        expect(WUXING_CONFIG[element].textClass).toBeDefined()
        expect(WUXING_CONFIG[element].accentClass).toBeDefined()
        expect(WUXING_CONFIG[element].ringClass).toBeDefined()
        expect(WUXING_CONFIG[element].gradientClass).toBeDefined()
        expect(WUXING_CONFIG[element].gradientFrom).toBeDefined()
        expect(WUXING_CONFIG[element].gradientTo).toBeDefined()
      }
    })

    it('should have correct emoji for each element', () => {
      expect(WUXING_CONFIG['金'].emoji).toBe('✨')
      expect(WUXING_CONFIG['木'].emoji).toBe('🌿')
      expect(WUXING_CONFIG['水'].emoji).toBe('💧')
      expect(WUXING_CONFIG['火'].emoji).toBe('🔥')
      expect(WUXING_CONFIG['土'].emoji).toBe('🌻')
    })

    it('should have correct colors for each element (aligned with globals.css)', () => {
      expect(WUXING_CONFIG['金'].color).toBe('#C5D0D8')  // 春霜银
      expect(WUXING_CONFIG['木'].color).toBe('#3DA35D')   // 春芽绿
      expect(WUXING_CONFIG['水'].color).toBe('#4A90C4')   // 春雨青
      expect(WUXING_CONFIG['火'].color).toBe('#D4656B')   // 春桃粉
      expect(WUXING_CONFIG['土'].color).toBe('#B89B5E')   // 春泥黄
    })
  })

  describe('getWuxingConfig', () => {
    it('should return config for valid element', () => {
      const config = getWuxingConfig('木')
      expect(config.element).toBe('木')
    })

    it('should return default (金) for undefined', () => {
      const config = getWuxingConfig(undefined)
      expect(config.element).toBe('金')
    })

    it('should return default (金) for invalid element', () => {
      const config = getWuxingConfig('invalid')
      expect(config.element).toBe('金')
    })

    it('should return default (金) for empty string', () => {
      const config = getWuxingConfig('')
      expect(config.element).toBe('金')
    })
  })

  describe('TIANGAN_WUXING', () => {
    it('should map all 10 heavenly stems', () => {
      expect(Object.keys(TIANGAN_WUXING)).toHaveLength(10)
      expect(Object.keys(TIANGAN_WUXING)).toEqual(
        expect.arrayContaining(['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'])
      )
    })

    it('should map 甲乙 to 木', () => {
      expect(TIANGAN_WUXING['甲']).toBe('木')
      expect(TIANGAN_WUXING['乙']).toBe('木')
    })

    it('should map 丙丁 to 火', () => {
      expect(TIANGAN_WUXING['丙']).toBe('火')
      expect(TIANGAN_WUXING['丁']).toBe('火')
    })

    it('should map 戊己 to 土', () => {
      expect(TIANGAN_WUXING['戊']).toBe('土')
      expect(TIANGAN_WUXING['己']).toBe('土')
    })

    it('should map 庚辛 to 金', () => {
      expect(TIANGAN_WUXING['庚']).toBe('金')
      expect(TIANGAN_WUXING['辛']).toBe('金')
    })

    it('should map 壬癸 to 水', () => {
      expect(TIANGAN_WUXING['壬']).toBe('水')
      expect(TIANGAN_WUXING['癸']).toBe('水')
    })
  })

  describe('DIZHI_WUXING', () => {
    it('should map all 12 earthly branches', () => {
      expect(Object.keys(DIZHI_WUXING)).toHaveLength(12)
    })

    it('should map 寅卯 to 木', () => {
      expect(DIZHI_WUXING['寅']).toBe('木')
      expect(DIZHI_WUXING['卯']).toBe('木')
    })

    it('should map 巳午 to 火', () => {
      expect(DIZHI_WUXING['巳']).toBe('火')
      expect(DIZHI_WUXING['午']).toBe('火')
    })

    it('should map 辰戌丑未 to 土', () => {
      expect(DIZHI_WUXING['辰']).toBe('土')
      expect(DIZHI_WUXING['戌']).toBe('土')
      expect(DIZHI_WUXING['丑']).toBe('土')
      expect(DIZHI_WUXING['未']).toBe('土')
    })

    it('should map 申酉 to 金', () => {
      expect(DIZHI_WUXING['申']).toBe('金')
      expect(DIZHI_WUXING['酉']).toBe('金')
    })

    it('should map 亥子 to 水', () => {
      expect(DIZHI_WUXING['亥']).toBe('水')
      expect(DIZHI_WUXING['子']).toBe('水')
    })
  })
})
