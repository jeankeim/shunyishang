'use client'

import { useEffect, useState } from 'react'

/**
 * 跟随系统「减弱动态效果」偏好。
 * SSR 首帧返回 false，挂载后同步真实值（避免服务端/首屏不一致）。
 */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReduced(mq.matches)
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  return reduced
}
