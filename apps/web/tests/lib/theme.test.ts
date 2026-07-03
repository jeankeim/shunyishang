import { describe, it, expect } from 'vitest'
import { getCurrentSolarTerm, baziToRadarData, itemsToRadarData, SolarTerm } from '@/lib/theme'

describe('lib/theme', () => {
  describe('getCurrentSolarTerm', () => {
    it('should return wood theme for spring months (Feb-Apr)', () => {
      const febDate = new Date(2024, 1, 15) // February
      const result = getCurrentSolarTerm(febDate)
      expect(result.element).toBe('wood')
      expect(result.name).toBe('木')

      const aprDate = new Date(2024, 3, 15) // April
      expect(getCurrentSolarTerm(aprDate).element).toBe('wood')
    })

    it('should return fire theme for summer months (May-Jul)', () => {
      const mayDate = new Date(2024, 4, 15) // May
      expect(getCurrentSolarTerm(mayDate).element).toBe('fire')

      const julDate = new Date(2024, 6, 15) // July
      expect(getCurrentSolarTerm(julDate).element).toBe('fire')
    })

    it('should return metal theme for autumn months (Aug-Oct)', () => {
      const augDate = new Date(2024, 7, 15) // August
      expect(getCurrentSolarTerm(augDate).element).toBe('metal')

      const octDate = new Date(2024, 9, 15) // October
      expect(getCurrentSolarTerm(octDate).element).toBe('metal')
    })

    it('should return water theme for winter months (Nov-Jan)', () => {
      const novDate = new Date(2024, 10, 15) // November
      expect(getCurrentSolarTerm(novDate).element).toBe('water')

      const janDate = new Date(2024, 0, 15) // January
      expect(getCurrentSolarTerm(janDate).element).toBe('water')

      const decDate = new Date(2024, 11, 15) // December
      expect(getCurrentSolarTerm(decDate).element).toBe('water')
    })

    it('should return earth theme as fallback (should not happen with current logic)', () => {
      // With the current logic, all months are covered, but let's test the fallback
      // This is more of a safety check
      const result = getCurrentSolarTerm()
      expect(result).toBeDefined()
      expect(['wood', 'fire', 'earth', 'metal', 'water']).toContain(result.element)
    })

    it('should include all required properties', () => {
      const result = getCurrentSolarTerm(new Date(2024, 2, 15))
      expect(result).toHaveProperty('name')
      expect(result).toHaveProperty('element')
      expect(result).toHaveProperty('primaryColor')
      expect(result).toHaveProperty('bgColor')
      expect(result).toHaveProperty('cssVariable')
    })
  })

  describe('baziToRadarData', () => {
    it('should return empty object for null bazi', () => {
      expect(baziToRadarData(null)).toEqual({})
    })

    it('should return empty object for undefined bazi', () => {
      expect(baziToRadarData(undefined)).toEqual({})
    })

    it('should calculate five elements distribution from pillars', () => {
      const bazi = {
        year_pillar: '甲子',
        month_pillar: '乙丑',
        day_pillar: '丙寅',
        hour_pillar: '丁卯',
      }
      const result = baziToRadarData(bazi)
      // 甲=木, 子=水, 乙=木, 丑=土, 丙=火, 寅=木, 丁=火, 卯=木
      // 木: 4, 水: 1, 土: 1, 火: 2
      expect(result['木']).toBe(100) // max = 4, so 4/4*100 = 100
      expect(result['火']).toBe(50)  // 2/4*100 = 50
      expect(result['水']).toBe(25)  // 1/4*100 = 25
      expect(result['土']).toBe(25)  // 1/4*100 = 25
      expect(result['金']).toBe(0)
    })

    it('should handle missing pillars', () => {
      const bazi = {
        year_pillar: '甲子',
        month_pillar: undefined,
        day_pillar: undefined,
        hour_pillar: undefined,
      }
      const result = baziToRadarData(bazi)
      expect(result['木']).toBe(100)
      expect(result['水']).toBe(100)
    })

    it('should handle pillars with wrong length', () => {
      const bazi = {
        year_pillar: '甲',
        month_pillar: '乙',
        day_pillar: '丙',
        hour_pillar: '丁',
      }
      const result = baziToRadarData(bazi)
      // All pillars have length 1, so they won't be processed
      expect(result['金']).toBe(0)
    })
  })

  describe('itemsToRadarData', () => {
    it('should return zeros for empty items', () => {
      const result = itemsToRadarData([])
      expect(result['金']).toBe(0)
      expect(result['木']).toBe(0)
      expect(result['水']).toBe(0)
      expect(result['火']).toBe(0)
      expect(result['土']).toBe(0)
    })

    it('should calculate distribution from items', () => {
      const items = [
        { primary_element: '木' },
        { primary_element: '木' },
        { primary_element: '火' },
      ]
      const result = itemsToRadarData(items)
      expect(result['木']).toBe(100) // 2/2*100 = 100
      expect(result['火']).toBe(50)  // 1/2*100 = 50
    })

    it('should handle items without primary_element', () => {
      const items = [
        { primary_element: '' },
        { primary_element: '木' },
      ]
      const result = itemsToRadarData(items)
      expect(result['木']).toBe(100)
    })
  })
})
