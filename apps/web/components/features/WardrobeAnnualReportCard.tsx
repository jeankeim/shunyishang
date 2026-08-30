'use client'

/**
 * 衣橱年度报告（批次三 3.2）
 *
 * 形态：衣橱页入口卡（柜体暖色，与相邻面板一致）→「查看完整报告」弹层（沿用运势报告的
 * mystic 令牌）→「生成分享海报」（复用通用 base64 海报链路）。
 * 口径：报告里的数字全部来自后端 SQL 聚合，前端不做任何推算；文案为生活习惯观察与
 * 传统文化参考，不作吉凶断言，也不出现价格/金额（个人备案版约束）。
 */

import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { createPortal } from 'react-dom'
import { BookOpenText, Download, ImagePlus, Loader2, X } from 'lucide-react'
import {
  generateWardrobeReport,
  getWardrobeReport,
  postPosterBase64,
  type WardrobeReport,
  type WardrobeReportItem,
  type WardrobeReportQuota,
} from '@/lib/api'
import { toast } from '@/components/ui'
import { ELEMENT_THEME_MAP } from '@/lib/poster-templates'
import { getImageUrl } from '@/lib/image'
import { getWuxingConfig } from '@/lib/wuxing-config'
import { useUserStore } from '@/store/user'
import { ImageLightbox } from './ImageLightbox'

/** pending 回查：worker 还在跑时周期刷新，最多 12 次（约 60 秒）后停手，避免无 worker 环境下无限轮询 */
const PENDING_POLL_MS = 5000
const PENDING_POLL_MAX = 12

/** 报告分段（key 与后端 narrative 字段一一对应） */
const NARRATIVE_SECTIONS = [
  { key: 'overall', label: '年度总览' },
  { key: 'top_item', label: '穿得最多的一件' },
  { key: 'idle_item', label: '最久没动的一件' },
  { key: 'element_story', label: '本命色' },
  { key: 'trend', label: '月度五行变迁' },
  { key: 'advice', label: '给明年的一条建议' },
] as const

export function WardrobeAnnualReportCard() {
  const currentYear = new Date().getFullYear()
  const user = useUserStore((state) => state.user)
  const [year, setYear] = useState(currentYear)
  const [report, setReport] = useState<WardrobeReport | null>(null)
  const [quota, setQuota] = useState<WardrobeReportQuota | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [open, setOpen] = useState(false)
  const [posterUrl, setPosterUrl] = useState<string | null>(null)
  const [posterLoading, setPosterLoading] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    getWardrobeReport(year)
      .then((result) => {
        if (!result) {
          setReport(null)
          setQuota(null)
          return
        }
        setReport(result.report)
        setQuota(result.quota)
      })
      .finally(() => setLoading(false))
  }, [year])

  useEffect(() => { load() }, [load])

  const status = report?.status ?? null

  // 行还是 pending 说明任务在 worker 手里，周期回直到 ready / failed
  useEffect(() => {
    if (status !== 'pending') return
    let ticks = 0
    const timer = setInterval(() => {
      ticks += 1
      load()
      if (ticks >= PENDING_POLL_MAX) clearInterval(timer)
    }, PENDING_POLL_MS)
    return () => clearInterval(timer)
  }, [status, load])

  const isBusy = generating || status === 'pending'
  const stats = report?.content?.stats
  const narrative = report?.content?.narrative
  const exhausted = !!quota && quota.remaining <= 0

  async function handleGenerate() {
    if (isBusy) return
    setGenerating(true)
    try {
      await generateWardrobeReport(year)
      toast.success(`${year} 年衣橱报告已生成`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '报告生成失败，请稍后重试')
    } finally {
      setGenerating(false)
      // 结果以服务端为准：超时或失败也回查一次，顺带刷新额度
      load()
    }
  }

  /** 分享海报：复用通用 base64 海报链路，主题色取本命色对应五行主题 */
  async function handlePoster() {
    if (!report || posterLoading) return
    setPosterLoading(true)
    try {
      const pieces = [stats?.top_worn_item, stats?.idle_item]
        .filter((x): x is WardrobeReportItem => !!x)
        .map((x) => ({
          id: x.id,
          name: x.name,
          category: x.category,
          image_url: x.image_url,
          primary_element: x.primary_element,
        }))
      const lucky = stats?.lucky_element
      const res = await postPosterBase64({
        layout: 'wuxing',
        title: report.title,
        items: pieces,
        xiyong_elements: lucky ? [lucky] : [],
        theme: (lucky && ELEMENT_THEME_MAP[lucky]) || 'wood',
        quote: narrative?.overall || '',
        username: user?.nickname || user?.phone || '',
      })
      if (!res?.image) {
        toast.error('海报生成失败，请稍后重试')
        return
      }
      setPosterUrl(`data:image/png;base64,${res.image}`)
    } finally {
      setPosterLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="w-full rounded-2xl sm:rounded-3xl border border-stone-300/70 bg-gradient-to-b from-[#F6F2EC] to-[#EAE2D6] p-3 sm:p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_18px_36px_-24px_rgba(87,75,62,0.45)]">
        <div className="mb-2 h-4 w-32 animate-pulse rounded bg-white/50" />
        <div className="h-9 animate-pulse rounded-xl bg-white/50" />
      </div>
    )
  }

  // 接口不可用时不占位（未登录 / 服务异常都会静默为 null）
  if (!quota) return null

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full rounded-2xl sm:rounded-3xl border border-stone-300/70 bg-gradient-to-b from-[#F6F2EC] to-[#EAE2D6] p-3 sm:p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_18px_36px_-24px_rgba(87,75,62,0.45)]"
      >
        <div className="flex flex-wrap items-start justify-between gap-2 px-1">
          <div className="min-w-0">
            <span className="text-[10px] uppercase tracking-[0.2em] text-[#6F5D4B]/70">衣橱 · 年度报告</span>
            <h3 className="mt-0.5 text-[15px] font-semibold text-[#4A3F33]" style={{ fontFamily: 'serif' }}>
              {report?.generated && report.title ? report.title : `${year} 年的衣橱故事`}
            </h3>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setYear((y) => y - 1)}
              aria-label="上一年"
              className="rounded-md px-2 py-1 text-[11px] text-[#6F5D4B]/70 transition-colors hover:bg-white/70 hover:text-[#4A3F33] touch-feedback"
            >
              上一年
            </button>
            <span className="min-w-[3rem] text-center text-xs tabular-nums text-[#6F5D4B]">{year} 年</span>
            <button
              type="button"
              onClick={() => setYear((y) => Math.min(currentYear, y + 1))}
              disabled={year >= currentYear}
              aria-label="下一年"
              className="rounded-md px-2 py-1 text-[11px] text-[#6F5D4B]/70 transition-colors hover:bg-white/70 hover:text-[#4A3F33] disabled:opacity-30 disabled:hover:bg-transparent touch-feedback"
            >
              下一年
            </button>
          </div>
        </div>

        {report?.generated ? (
          <>
            <p className="mt-2 px-1 text-xs leading-relaxed text-[#6F5D4B]">
              {report.summary || narrative?.overall || `${year} 年的衣橱已经盘点好了。`}
            </p>
            <div className="mt-2.5 flex flex-wrap gap-2 px-1">
              <button
                type="button"
                onClick={() => setOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-xl bg-[#4A3F33] px-4 py-2 text-[13px] font-medium text-[#F6F2EC] transition-opacity hover:opacity-90 touch-feedback"
              >
                <BookOpenText className="w-4 h-4" /> 查看完整报告
              </button>
              <button
                type="button"
                onClick={handlePoster}
                disabled={posterLoading}
                className="inline-flex items-center gap-1.5 rounded-xl border border-[#6F5D4B]/15 bg-white/60 px-4 py-2 text-[13px] text-[#6F5D4B] transition-colors hover:bg-white/90 disabled:opacity-50 touch-feedback"
              >
                {posterLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ImagePlus className="w-4 h-4" />}
                {posterLoading ? '海报生成中…' : '生成分享海报'}
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="mt-2 px-1 text-xs leading-relaxed text-[#6F5D4B]/80">
              {status === 'failed'
                ? '上次生成没成功，可以再试一次。'
                : '把你这一年的穿搭日记、常穿的那件和最长情的闲置，汇成一份可读的盘点。'}
            </p>
            <div className="mt-2.5 flex flex-wrap items-center gap-2 px-1">
              <button
                type="button"
                onClick={handleGenerate}
                disabled={isBusy || exhausted}
                className="inline-flex items-center gap-1.5 rounded-xl bg-[#4A3F33] px-4 py-2 text-[13px] font-medium text-[#F6F2EC] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 touch-feedback"
              >
                {isBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <BookOpenText className="w-4 h-4" />}
                {isBusy ? '正在盘点你的衣橱…' : `生成 ${year} 年衣橱报告`}
              </button>
              <span className="text-[11px] text-[#6F5D4B]/70">
                {exhausted
                  ? `本年 ${quota.limit} 次机会已用完`
                  : `免费 · 本年还可生成 ${quota.remaining} / ${quota.limit} 次`}
              </span>
            </div>
          </>
        )}
      </motion.div>

      {/* 报告正文弹层 */}
      {open && report?.content && typeof document !== 'undefined' && createPortal(
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
          onClick={() => setOpen(false)}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="mystic-modal w-full max-w-lg rounded-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 内层独立滚动容器：.mystic-modal 的 overflow:hidden 只用于圆角/星象裁切，
                滚动必须放在这一层，否则内容会被外层裁掉且无法滚动 */}
            <div className="relative z-10 max-h-[85vh] overflow-y-auto overscroll-contain p-6">
              <div className="mb-4 flex items-center justify-between gap-2">
                <h3 className="mystic-heading text-lg font-bold">{report.title}</h3>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  aria-label="关闭报告"
                  className="mystic-subtle hover:text-white"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {stats && <ReportFacts stats={stats} />}

              {narrative && (
                <div className="mt-4 space-y-3 text-sm">
                  {NARRATIVE_SECTIONS.map(({ key, label }) => (
                    narrative[key] && (
                      <div key={key} className="mystic-card p-3">
                        <h4 className="mystic-gold mb-1 font-medium">{label}</h4>
                        <p className="leading-relaxed" style={{ color: '#cfc7dd' }}>{narrative[key]}</p>
                      </div>
                    )
                  ))}
                </div>
              )}

              {stats && <ElementTrend stats={stats} />}

              <p className="mt-4 text-[10px] leading-relaxed mystic-subtle">
                报告数字取自你的衣橱与穿搭日记，文案为生活习惯观察与传统文化参考，不作吉凶断言。
              </p>
            </div>
          </motion.div>
        </div>,
        document.body
      )}

      {/* 海报预览：移动端长按保存，桌面端显式下载 */}
      {posterUrl && (
        <ImageLightbox
          imageUrl={posterUrl}
          alt={`${year} 年衣橱年度报告海报`}
          caption="长按图片可保存 · 下载后即可分享"
          onClose={() => setPosterUrl(null)}
          actions={
            <a
              href={posterUrl}
              download={`${year}年衣橱年度报告.png`}
              className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-white/90 text-[var(--brand-heading)] text-sm font-medium hover:bg-white transition-colors"
            >
              <Download className="w-4 h-4" /> 下载到本地
            </a>
          }
        />
      )}
    </>
  )
}

// ── 弹层内的事实区 ────────────────────────────────────────────────────────────

function ReportFacts({ stats }: { stats: NonNullable<WardrobeReport['content']['stats']> }) {
  const cells = [
    { value: `${stats.total_items} 件`, label: '衣橱在库' },
    { value: `${stats.new_this_year} 件`, label: `${stats.year} 年新增` },
    { value: `${stats.diary_count} 套`, label: '穿搭日记' },
    { value: `${stats.worn_this_year} 件`, label: `${stats.year} 年上身` },
  ]
  const featured = [stats.top_worn_item, stats.idle_item].filter(
    (x): x is WardrobeReportItem => !!x,
  )

  return (
    <>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {cells.map((cell) => (
          <div key={cell.label} className="mystic-card px-2 py-2 text-center">
            <div className="mystic-heading text-[13px] font-semibold tabular-nums">{cell.value}</div>
            <div className="mystic-subtle mt-0.5 text-[10px]">{cell.label}</div>
          </div>
        ))}
      </div>

      {featured.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {featured.map((item, index) => (
            <div key={`${item.id}-${index}`} className="mystic-card flex min-w-0 flex-1 items-center gap-2 p-2">
              {item.image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={getImageUrl(item.image_url)}
                  alt={item.name}
                  className="h-9 w-9 shrink-0 rounded-md object-cover"
                />
              ) : (
                <div
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-[11px]"
                  style={{
                    backgroundColor: `${getWuxingConfig(item.primary_element || '').color}22`,
                    color: getWuxingConfig(item.primary_element || '').color,
                  }}
                >
                  {item.primary_element || '衣'}
                </div>
              )}
              <div className="min-w-0">
                <p className="truncate text-xs font-medium" style={{ color: '#e8e2f2' }}>
                  {item.name || '未命名衣物'}
                </p>
                <p className="mystic-subtle mt-0.5 truncate text-[10px]">
                  {index === 0
                    ? `今年出现 ${item.wear_times ?? 0} 次${item.category ? ` · ${item.category}` : ''}`
                    : `已 ${item.idle_days ?? 0} 天没被动过`}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {stats.declutter.total_processed > 0 && (
        <p className="mystic-subtle mt-2 text-[11px] leading-relaxed">{stats.declutter.summary}</p>
      )}
    </>
  )
}

/** 月度元素变迁：一行色点，读得出这一年偏哪一行 */
function ElementTrend({ stats }: { stats: NonNullable<WardrobeReport['content']['stats']> }) {
  const months = stats.monthly_elements.filter((m) => m.dominant)
  if (!months.length) return null

  return (
    <div className="mystic-card mt-4 p-3">
      <div className="mystic-subtle mb-2 text-[10px] uppercase tracking-[0.18em]">每个月偏哪一行</div>
      <div className="flex flex-wrap gap-x-3 gap-y-1.5">
        {months.map((m) => (
          <span key={m.month} className="inline-flex items-center gap-1 text-[11px]" style={{ color: '#cfc7dd' }}>
            <span className="mystic-subtle">{m.label}</span>
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: getWuxingConfig(m.dominant || '').color }}
            />
            {m.dominant}
          </span>
        ))}
      </div>
    </div>
  )
}
