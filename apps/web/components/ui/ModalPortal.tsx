'use client'

import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'

/**
 * 弹窗 Portal 容器：把弹层挂到 document.body 下渲染。
 *
 * 背景：页面 Tab 内容层带有 framer-motion 进场动画（transform/opacity），
 * 这些祖先会把后代 fixed 定位的包含块从视口劫持为动画容器，导致弹窗
 * 被挤出视口、被底部导航遮挡。Portal 到 body 可彻底脱离祖先影响。
 *
 * mounted 守卫：SSR 阶段不调用 createPortal（服务端无 document），
 * 首帧返回 null 与 SSR 输出一致，避免 hydration 不匹配。
 */
export function ModalPortal({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  if (!mounted) return null
  return createPortal(children, document.body)
}
