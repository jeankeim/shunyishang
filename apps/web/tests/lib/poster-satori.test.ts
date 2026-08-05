/**
 * poster-satori 纯函数测试（阶段2）
 */
import { describe, it, expect } from 'vitest'
import {
  pickSatoriMainIndex,
  truncateText,
  wrapSatoriText,
  SATORI_GUOFENG_THEMES,
  SATORI_ELEMENT_COLORS,
  GuofengSatori,
} from '@/lib/poster-satori'

describe('lib/poster-satori', () => {
  describe('pickSatoriMainIndex', () => {
    it('按品类优先级选择主件：外套 > 上装', () => {
      const items = [
        { name: '戒指', category: '配饰' },
        { name: '衬衫', category: '上装' },
        { name: '风衣', category: '外套' },
      ]
      expect(pickSatoriMainIndex(items)).toBe(2)
    })

    it('无优先品类时取首件', () => {
      const items = [{ name: '戒指', category: '配饰' }, { name: '鞋', category: '鞋履' }]
      expect(pickSatoriMainIndex(items)).toBe(0)
    })
  })

  describe('truncateText', () => {
    it('短文本不截断', () => {
      expect(truncateText('短文本', 28, 430)).toBe('短文本')
    })

    it('超长文本截断并加省略号', () => {
      const result = truncateText('这是一段很长很长的推荐理由文字', 28, 100)
      expect(result.endsWith('…')).toBe(true)
      expect(result.length).toBeLessThan(16)
    })

    it('ASCII 按半角宽度估算', () => {
      expect(truncateText('abcdefgh', 20, 400)).toBe('abcdefgh')
    })
  })

  describe('wrapSatoriText', () => {
    it('短文本单行', () => {
      expect(wrapSatoriText('短文本', 28, 500)).toEqual(['短文本'])
    })

    it('长文本折多行且内容完整', () => {
      const lines = wrapSatoriText('甲乙丙丁戊己庚辛壬癸', 28, 90)
      expect(lines.length).toBeGreaterThan(1)
      expect(lines.join('')).toBe('甲乙丙丁戊己庚辛壬癸')
    })
  })

  describe('主题常量', () => {
    it('五行主题齐全且含必要色值', () => {
      for (const key of ['wood', 'fire', 'earth', 'metal', 'water']) {
        expect(SATORI_GUOFENG_THEMES[key]).toBeDefined()
        expect(SATORI_GUOFENG_THEMES[key].primary).toMatch(/^#[0-9A-F]{6}$/i)
        expect(SATORI_GUOFENG_THEMES[key].paper).toMatch(/^#[0-9A-F]{6}$/i)
      }
    })

    it('五行传统色与后端一致', () => {
      expect(SATORI_ELEMENT_COLORS['木']).toBe('#4E8560')
      expect(SATORI_ELEMENT_COLORS['水']).toBe('#3F6C8E')
    })
  })

  describe('GuofengSatori', () => {
    it('返回 React 元素树（可被 Satori 渲染）', () => {
      const node = GuofengSatori({
        title: '今日五行穿搭推荐',
        items: [
          { name: '风衣', category: '外套', primary_element: '水', reason: '水生木' },
          { name: '衬衫', category: '上装', primary_element: '金' },
        ],
        xiyong_elements: ['水', '木'],
        theme: 'water',
        quote: '水木相生',
        username: '测试',
        lunar: '丙午年六月廿三',
        date: '2026-08-05',
      })
      expect(node).toBeTruthy()
    })

    it('空数据不抛错', () => {
      const node = GuofengSatori({
        title: '空衣单',
        items: [],
        xiyong_elements: [],
        theme: 'unknown',
        date: '2026-08-05',
      })
      expect(node).toBeTruthy()
    })
  })
})
