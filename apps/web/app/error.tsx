'use client'

import { useEffect } from 'react'

/**
 * 全局错误边界
 * 重点处理 ChunkLoadError：部署新版本后，旧页面懒加载已被替换的 chunk 会 404。
 * 检测到该错误时自动刷新一次拿到新版本（sessionStorage 防刷新循环）。
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  const isChunkError =
    error.name === 'ChunkLoadError' ||
    /Loading chunk .* failed/i.test(error.message) ||
    /Failed to fetch dynamically imported module/i.test(error.message)

  useEffect(() => {
    if (!isChunkError) return
    const KEY = 'chunk-error-reloaded'
    try {
      if (!sessionStorage.getItem(KEY)) {
        sessionStorage.setItem(KEY, '1')
        window.location.reload()
      }
    } catch {
      // sessionStorage 不可用时直接刷新（无防循环，但属极端场景）
      window.location.reload()
    }
  }, [isChunkError])

  // 正常加载成功后清除刷新标记，下次部署仍可自动恢复
  useEffect(() => {
    return () => {
      try {
        sessionStorage.removeItem('chunk-error-reloaded')
      } catch {
        // ignore
      }
    }
  }, [])

  // chunk 错误刷新中，避免闪现错误 UI
  if (isChunkError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">正在加载新版本…</p>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
      <h2 className="font-serif text-xl font-semibold text-foreground">页面出了点小问题</h2>
      <p className="text-sm text-muted-foreground">请稍后重试，若持续出现请刷新页面</p>
      <button
        onClick={reset}
        className="rounded-full bg-primary px-6 py-2 text-sm text-primary-foreground transition-opacity hover:opacity-90"
      >
        重试
      </button>
    </div>
  )
}
