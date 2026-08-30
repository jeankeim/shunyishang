'use client'

// 衣橱柜体原型 harness —— 三个衣橱视觉方向，通过底部选择器切换。
// 行为契约见 prototype skill PICKER.md：1-N / ←→ 切换，R 重放，?v=N 持久化。
import { Suspense, useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import './picker.css'
import { MuyuVariant } from './variants/Muyu'
import { SujianVariant } from './variants/Sujian'
import { JingeVariant } from './variants/Jinge'

const VARIANTS = [
  { name: '木语', Component: MuyuVariant },
  { name: '素简', Component: SujianVariant },
  { name: '锦阁', Component: JingeVariant },
]

function PrototypeHarness() {
  const searchParams = useSearchParams()
  const initial = Math.min(Math.max(parseInt(searchParams.get('v') || '1', 10) || 1, 1), VARIANTS.length) - 1

  const [current, setCurrent] = useState(initial)
  const [replayKey, setReplayKey] = useState(0)
  const pickerRef = useRef<HTMLElement>(null)
  const highlightRef = useRef<HTMLSpanElement>(null)
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([])

  const moveHighlight = useCallback(() => {
    const el = itemRefs.current[current]
    const highlight = highlightRef.current
    if (!el || !highlight) return
    highlight.style.width = `${el.offsetWidth}px`
    highlight.style.transform = `translateX(${el.offsetLeft}px)`
  }, [current])

  // refs + layout effect 测量高亮位置（框架化的参考接线）
  useLayoutEffect(() => {
    moveHighlight()
  }, [moveHighlight, replayKey])

  // 首帧后才启用滑动，避免加载时动画
  useEffect(() => {
    const raf = requestAnimationFrame(() => requestAnimationFrame(() => {
      pickerRef.current?.setAttribute('data-ready', '')
    }))
    return () => cancelAnimationFrame(raf)
  }, [])

  useEffect(() => {
    window.addEventListener('resize', moveHighlight)
    return () => window.removeEventListener('resize', moveHighlight)
  }, [moveHighlight])

  const setActive = useCallback((i: number) => {
    if (i < 0 || i >= VARIANTS.length) return
    setCurrent(i)
    const url = new URL(window.location.href)
    url.searchParams.set('v', String(i + 1))
    window.history.replaceState(null, '', url)
  }, [])

  const replay = useCallback(() => setReplayKey((k) => k + 1), [])

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName) || target.isContentEditable) return
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const num = parseInt(e.key, 10)
      if (num >= 1 && num <= VARIANTS.length) setActive(num - 1)
      else if (e.key === 'ArrowRight') setActive((current + 1) % VARIANTS.length)
      else if (e.key === 'ArrowLeft') setActive((current - 1 + VARIANTS.length) % VARIANTS.length)
      else if (e.key === 'r' || e.key === 'R') replay()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [current, setActive, replay])

  const Active = VARIANTS[current].Component

  return (
    <>
      {/* key 变化 → 变体重新挂载，入场动画重放；切换本身无过渡 */}
      <div key={`${current}-${replayKey}`}>
        <Active />
      </div>

      <nav ref={pickerRef} className="proto-picker" aria-label="Prototype variants">
        <span ref={highlightRef} className="proto-picker-highlight" aria-hidden="true" />
        {VARIANTS.map((v, i) => (
          <button
            key={v.name}
            ref={(el) => { itemRefs.current[i] = el }}
            className="proto-picker-item"
            {...(i === current ? { 'data-active': true, 'aria-current': 'true' as const } : {})}
            onClick={() => setActive(i)}
          >
            {v.name}
          </button>
        ))}
        <span className="proto-picker-divider" aria-hidden="true" />
        <button className="proto-picker-item proto-picker-replay" aria-label="Replay animation (R)" onClick={replay}>
          ↻
        </button>
      </nav>
    </>
  )
}

export default function PrototypePage() {
  return (
    <Suspense fallback={null}>
      <PrototypeHarness />
    </Suspense>
  )
}
