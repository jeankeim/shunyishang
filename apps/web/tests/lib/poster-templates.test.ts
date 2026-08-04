import { describe, it, expect } from 'vitest'
import {
  WUXING_THEMES,
  POSTER_TEMPLATES,
  DEFAULT_TEMPLATE,
  DEFAULT_THEME,
  ELEMENT_THEME_MAP,
  PosterTemplate,
  ColorTheme,
} from '@/lib/poster-templates'

describe('lib/poster-templates', () => {
  describe('WUXING_THEMES', () => {
    it('should have themes for all five elements', () => {
      expect(Object.keys(WUXING_THEMES)).toEqual(['fire', 'wood', 'earth', 'metal', 'water'])
    })

    it('should have correct theme for fire', () => {
      expect(WUXING_THEMES.fire.name).toBe('火')
      expect(WUXING_THEMES.fire.primary).toBe('#FF6B6B')
    })

    it('should have correct theme for wood', () => {
      expect(WUXING_THEMES.wood.name).toBe('木')
      expect(WUXING_THEMES.wood.primary).toBe('#4ADE80')
    })

    it('should have correct theme for earth', () => {
      expect(WUXING_THEMES.earth.name).toBe('土')
      expect(WUXING_THEMES.earth.primary).toBe('#FCD34D')
    })

    it('should have correct theme for metal', () => {
      expect(WUXING_THEMES.metal.name).toBe('金')
      expect(WUXING_THEMES.metal.primary).toBe('#F3F4F6')
    })

    it('should have correct theme for water', () => {
      expect(WUXING_THEMES.water.name).toBe('水')
      expect(WUXING_THEMES.water.primary).toBe('#60A5FA')
    })

    it('should have all required properties for each theme', () => {
      for (const key of Object.keys(WUXING_THEMES)) {
        const theme = WUXING_THEMES[key]
        expect(theme).toHaveProperty('name')
        expect(theme).toHaveProperty('primary')
        expect(theme).toHaveProperty('secondary')
        expect(theme).toHaveProperty('background')
        expect(theme).toHaveProperty('text')
      }
    })
  })

  describe('POSTER_TEMPLATES', () => {
    it('should have 4 templates', () => {
      expect(POSTER_TEMPLATES).toHaveLength(4)
    })

    it('should have guofeng template', () => {
      const guofeng = POSTER_TEMPLATES.find(t => t.id === 'guofeng')
      expect(guofeng).toBeDefined()
      expect(guofeng?.name).toBe('宋锦国风')
      expect(guofeng?.layout).toBe('guofeng')
    })

    it('should have simple template', () => {
      const simple = POSTER_TEMPLATES.find(t => t.id === 'simple')
      expect(simple).toBeDefined()
      expect(simple?.name).toBe('简约风格')
      expect(simple?.layout).toBe('simple')
    })

    it('should have wuxing template', () => {
      const wuxing = POSTER_TEMPLATES.find(t => t.id === 'wuxing')
      expect(wuxing).toBeDefined()
      expect(wuxing?.name).toBe('五行风格')
      expect(wuxing?.layout).toBe('wuxing')
    })

    it('should have card template', () => {
      const card = POSTER_TEMPLATES.find(t => t.id === 'card')
      expect(card).toBeDefined()
      expect(card?.name).toBe('卡片风格')
      expect(card?.layout).toBe('card')
    })

    it('should have all required properties for each template', () => {
      for (const template of POSTER_TEMPLATES) {
        expect(template).toHaveProperty('id')
        expect(template).toHaveProperty('name')
        expect(template).toHaveProperty('thumbnail')
        expect(template).toHaveProperty('layout')
        expect(template).toHaveProperty('style')
        expect(template.style).toHaveProperty('background')
        expect(template.style).toHaveProperty('primaryColor')
        expect(template.style).toHaveProperty('secondaryColor')
        expect(template.style).toHaveProperty('fontFamily')
      }
    })
  })

  describe('DEFAULT_TEMPLATE', () => {
    it('should be the first template (guofeng)', () => {
      expect(DEFAULT_TEMPLATE.id).toBe('guofeng')
      expect(DEFAULT_TEMPLATE).toEqual(POSTER_TEMPLATES[0])
    })
  })

  describe('ELEMENT_THEME_MAP', () => {
    it('should map five elements to theme keys', () => {
      expect(ELEMENT_THEME_MAP['木']).toBe('wood')
      expect(ELEMENT_THEME_MAP['火']).toBe('fire')
      expect(ELEMENT_THEME_MAP['土']).toBe('earth')
      expect(ELEMENT_THEME_MAP['金']).toBe('metal')
      expect(ELEMENT_THEME_MAP['水']).toBe('water')
    })
  })

  describe('DEFAULT_THEME', () => {
    it('should be the fire theme', () => {
      expect(DEFAULT_THEME).toEqual(WUXING_THEMES.fire)
    })
  })
})
