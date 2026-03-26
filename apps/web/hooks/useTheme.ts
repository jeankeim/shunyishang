'use client'

import { useState, useEffect } from 'react'
import { getCurrentSolarTerm, SolarTerm } from '@/lib/theme'

export function useTheme() {
  const [currentTerm, setCurrentTerm] = useState<SolarTerm | null>(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setCurrentTerm(getCurrentSolarTerm())
    setMounted(true)
  }, [])

  return {
    currentTerm,
    mounted,
    isDark: true,
    cssVariable: currentTerm?.cssVariable || '142 76% 36%',
  }
}
