'use client'

import { useEffect, useState } from 'react'
import { useUserStore } from '@/store/user'
import { getCurrentSolarTerm, SolarTerm } from '@/lib/theme'

/**
 * 五行主题 Hook
 * - 已登录用户：根据 xiyong_elements[0] 设置 data-element 属性
 * - 未登录用户：根据当前节气自动切换主题
 */
export function useWuxingTheme() {
  const { user, isAuthenticated } = useUserStore()
  const [element, setElement] = useState<string>('')
  const [solarTerm, setSolarTerm] = useState<SolarTerm | null>(null)

  useEffect(() => {
    if (isAuthenticated && user?.xiyong_elements?.length) {
      // 已登录用户：使用喜用神第一个元素
      const el = user.xiyong_elements[0]
      setElement(el)
      applyElementToDOM(el)
    } else {
      // 未登录用户：使用节气主题
      const term = getCurrentSolarTerm()
      setSolarTerm(term)
      const el = elementToChinese(term.element)
      setElement(el)
      applyElementToDOM(el)
    }
  }, [isAuthenticated, user?.xiyong_elements])

  return {
    element,
    solarTerm,
    isUserElement: isAuthenticated && !!user?.xiyong_elements?.length,
  }
}

/**
 * 将五行元素映射到中文
 */
function elementToChinese(element: string): string {
  const map: Record<string, string> = {
    wood: '木',
    fire: '火',
    earth: '土',
    metal: '金',
    water: '水',
  }
  return map[element] || '木'
}

/**
 * 将 data-element 属性应用到 HTML 根元素
 */
function applyElementToDOM(element: string) {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-element', element)
  }
}
