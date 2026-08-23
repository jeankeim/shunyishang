'use client'

import { Type, Check } from 'lucide-react'
import { useFontSizeStore } from '@/store/fontSize'
import { FONT_SIZES } from '@/lib/font-sizes'
import { cn } from '@/lib/utils'

/**
 * 应用设置 - 字体大小（个人中心「我的」页内，适老化）
 * 小号=当前默认，中号/大号全站等比放大，点击即时生效并持久化
 */
export function FontSizeSettings() {
  const { fontSize, setFontSize } = useFontSizeStore()

  return (
    <section className="bg-white rounded-2xl p-5 shadow-sm border border-[var(--brand-border)]/40">
      <h3 className="text-lg font-semibold flex items-center gap-2 text-[var(--brand-heading)] pb-3 mb-4 border-b border-[var(--brand-border)]/40">
        <Type className="h-5 w-5 text-[var(--wuxing-metal)]" />
        字体大小
      </h3>
      <p className="text-sm text-[var(--brand-subtle)] mb-4">
        觉得字小看不清？调大后全站文字即时放大，方便长辈阅读（默认小号）
      </p>

      <div className="grid grid-cols-3 gap-3">
        {FONT_SIZES.map((f) => {
          const active = fontSize === f.id
          return (
            <button
              key={f.id}
              type="button"
              onClick={() => setFontSize(f.id)}
              aria-pressed={active}
              className={cn(
                'relative flex flex-col items-center gap-1 py-3 rounded-xl border-2 transition-all hover:scale-[1.02] active:scale-95',
                active
                  ? 'border-[var(--wuxing-wood)] bg-[var(--brand-surface)]/60 shadow-sm'
                  : 'border-transparent bg-[var(--brand-surface)]/30 hover:border-[var(--brand-border)]'
              )}
            >
              {/* 字号预览：用不同大小的「字」直观展示 */}
              <span
                className="font-semibold text-[var(--brand-heading)] leading-none"
                style={{ fontSize: `${f.px + 4}px` }}
              >
                字
              </span>
              <span className="text-sm font-medium text-[var(--brand-heading)]">
                {f.name}
              </span>
              <span className="text-xs text-[var(--brand-subtle)]">
                {f.desc}
              </span>
              {active && (
                <Check className="absolute top-1.5 right-1.5 w-4 h-4 text-[var(--wuxing-wood)]" />
              )}
            </button>
          )
        })}
      </div>
    </section>
  )
}
