'use client'

import { Palette, Check } from 'lucide-react'
import { useSkinStore } from '@/store/skin'
import { SKINS } from '@/lib/skins'
import { cn } from '@/lib/utils'

/**
 * 应用设置 - 皮肤选择（个人中心「我的」页内）
 * 列表式选择，点击即时全站生效并持久化；默认青瓷（auto）
 */
export function SkinSettings() {
  const { skin, setSkin } = useSkinStore()

  return (
    <section className="bg-white rounded-2xl p-5 shadow-sm border border-[var(--brand-border)]/40">
      <h3 className="text-lg font-semibold flex items-center gap-2 text-[var(--brand-heading)] pb-3 mb-4 border-b border-[var(--brand-border)]/40">
        <Palette className="h-5 w-5 text-[var(--wuxing-metal)]" />
        应用设置
      </h3>
      <p className="text-sm text-[var(--brand-subtle)] mb-4">
        选择你喜欢的界面皮肤，全站即时生效（默认青瓷）
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {SKINS.map((s) => {
          const active = skin === s.id
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => setSkin(s.id)}
              aria-pressed={active}
              className={cn(
                'flex items-center gap-3 p-3 rounded-xl border-2 text-left transition-all hover:scale-[1.02] active:scale-95',
                active
                  ? 'border-[var(--wuxing-wood)] bg-[var(--brand-surface)]/60 shadow-sm'
                  : 'border-transparent bg-[var(--brand-surface)]/30 hover:border-[var(--brand-border)]'
              )}
            >
              {/* 双色预览 */}
              <span
                className="w-9 h-9 rounded-full shrink-0 shadow-inner ring-1 ring-black/10"
                style={{
                  background: `linear-gradient(135deg, ${s.swatch[0]} 0 50%, ${s.swatch[1]} 50% 100%)`,
                }}
              />
              <span className="flex-1 min-w-0">
                <span className="flex items-center gap-2">
                  <span className="text-sm font-medium text-[var(--brand-heading)]">
                    {s.name}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[var(--brand-surface)] text-[var(--brand-subtle)]">
                    {s.mode === 'dark' ? '深色' : '浅色'}
                  </span>
                </span>
                <span className="block text-xs text-[var(--brand-subtle)] truncate mt-0.5">
                  {s.desc}
                </span>
              </span>
              {active && (
                <Check className="w-4 h-4 text-[var(--wuxing-wood)] shrink-0" />
              )}
            </button>
          )
        })}
      </div>
    </section>
  )
}
