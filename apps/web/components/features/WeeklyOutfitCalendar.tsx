'use client'

/**
 * 一周穿搭日历
 *
 * 首页「今日穿搭建议」下方的 7 天成套方案：天气取自 7 天预报，逐日按运势与
 * 季节打分选物，并控制同一单品跨天不过度复用。点击某一列展开当天整套，
 * 今天那一列可直接「今天就穿它」生成日记（与每日穿搭共用同一条日记链路）。
 */

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CalendarRange,
  Cloud,
  CloudFog,
  CloudLightning,
  CloudRain,
  CloudSnow,
  CloudSun,
  Download,
  Image as ImageIcon,
  RefreshCw,
  Sun,
  Sparkles,
  Check,
} from 'lucide-react'
import {
  getWeekOutfit,
  postWeekPoster,
  type DailyOutfit,
  type DailyOutfitItem,
  type WeekOutfit,
  type WeekOutfitDay,
} from '@/lib/api'
import { getImageUrl } from '@/lib/image'
import { hasTodayDiary, logOutfitAsDiary, loggedFlagKey, todayISO } from '@/lib/outfit-diary'
import { getWuxingConfig } from '@/lib/wuxing-config'
import { requestChatInputAutofill } from '@/lib/chatAutofill'
import { toast } from '@/components/ui/Toast'
import { useUserStore } from '@/store/user'
import { ItemDetailModal } from './ItemDetailModal'
import { OutfitPiecesView } from './OutfitPiecesView'
import { ImageLightbox } from './ImageLightbox'

/** 五行元素标签颜色（与今日穿搭卡一致） */
const ELEMENT_COLORS: Record<string, string> = {
  金: '#9CAFB8',
  木: '#3DA35D',
  水: '#4A90C4',
  火: '#C75B5B',
  土: '#B89B5E',
}

/** 单日「换一套」可选批次（后端 batch_index 限制 0-2） */
const MAX_DAY_BATCH = 3

/** 预报天气 → 图标（按关键词匹配，未识别时统一用云） */
function weatherIconOf(weather: string) {
  if (weather.includes('雪')) return CloudSnow
  if (weather.includes('雷')) return CloudLightning
  if (weather.includes('雨')) return CloudRain
  if (weather.includes('雾')) return CloudFog
  if (weather.includes('晴')) return Sun
  if (weather.includes('多云')) return CloudSun
  if (weather.includes('阴')) return Cloud
  return Cloud
}

/** 日期短标：MM-DD */
function shortDate(iso: string): string {
  const parts = iso.split('-')
  return parts.length === 3 ? `${parts[1]}-${parts[2]}` : iso
}

/** 喜用元素 → 海报五行主题 */
function elementToTheme(element: string): string {
  const map: Record<string, string> = { 木: 'wood', 火: 'fire', 土: 'earth', 金: 'metal', 水: 'water' }
  return map[element] || 'wood'
}

interface WeeklyOutfitCalendarProps {
  /** 是否已登录 */
  isAuthenticated: boolean
  /** 前端定位城市（与首页天气保持一致） */
  city?: string
}

export function WeeklyOutfitCalendar({ isAuthenticated, city }: WeeklyOutfitCalendarProps) {
  const user = useUserStore((state) => state.user)
  const [week, setWeek] = useState<WeekOutfit | null>(null)
  const [loading, setLoading] = useState(false)
  /** 展开的日期（null 表示只看 7 列） */
  const [expanded, setExpanded] = useState<string | null>(null)
  /** 单日换一套的覆盖结果与当前批次 */
  const [overrides, setOverrides] = useState<Record<string, WeekOutfitDay>>({})
  const [batches, setBatches] = useState<Record<string, number>>({})
  const [swapping, setSwapping] = useState<string | null>(null)
  const [logging, setLogging] = useState(false)
  const [logged, setLogged] = useState(false)
  const [selectedItem, setSelectedItem] = useState<DailyOutfitItem | null>(null)
  const [posterUrl, setPosterUrl] = useState<string | null>(null)
  const [posterLoading, setPosterLoading] = useState(false)

  const today = todayISO()
  const days = week?.days ?? []
  /** 单日「换一套」的覆盖结果优先于整周方案，展开面板与海报都以此为准 */
  const visibleDays = days.map((d) => overrides[d.date] || d)

  const fetchWeek = useCallback(async () => {
    if (!isAuthenticated) return
    setLoading(true)
    try {
      const result = await getWeekOutfit(city || undefined)
      // 带 date 参数才会返回单日结构，这里只可能拿到整周结构
      setWeek(result && 'days' in result ? (result as WeekOutfit) : null)
      // 整周重算后旧的单日覆盖即失效
      setOverrides({})
      setBatches({})
    } catch {
      setWeek(null)
    } finally {
      setLoading(false)
    }
  }, [isAuthenticated, city])

  useEffect(() => {
    if (isAuthenticated) fetchWeek()
  }, [isAuthenticated, fetchWeek])

  // 今日是否已有日记：本地标记只作首帧回显，最终以服务端为准
  useEffect(() => {
    if (!isAuthenticated) return
    setLogged(localStorage.getItem(loggedFlagKey()) === '1')
    let cancelled = false
    hasTodayDiary().then((exists) => {
      if (cancelled || exists === null) return
      setLogged(exists)
      if (exists) localStorage.setItem(loggedFlagKey(), '1')
      else localStorage.removeItem(loggedFlagKey())
    })
    return () => {
      cancelled = true
    }
  }, [isAuthenticated])

  /** 「今天就穿它」：与今日穿搭卡共用同一条一键日记链路 */
  async function handleWearToday(pieces: Array<{ id: number; category?: string }>) {
    if (!pieces.length || logging) return
    if (logged) {
      toast.info('今日已记入穿搭日记，去日记里看看或继续补充')
      window.location.hash = '#diary'
      return
    }
    setLogging(true)
    try {
      const res = await logOutfitAsDiary(pieces)
      if (res.ok) {
        localStorage.setItem(loggedFlagKey(), '1')
        setLogged(true)
        toast.success('已生成今日穿搭日记，拍照完善它')
      } else if (res.reason === 'exists') {
        localStorage.setItem(loggedFlagKey(), '1')
        setLogged(true)
        toast.info('今日已有穿搭日记，去日记里看看吧')
      } else {
        toast.error(res.message || '记录失败，请稍后重试')
        return
      }
      window.location.hash = '#diary'
    } finally {
      setLogging(false)
    }
  }

  /** 「衣橱缺 · 点这里补」：与今日穿搭卡同一跳出口，带元素语境跳推荐 */
  function handleFillMissing(category: string, luckyElement?: string) {
    requestChatInputAutofill(`推荐一件${luckyElement ? luckyElement + '属性的' : ''}${category}`)
    window.location.hash = '#chat'
  }

  /** 单日换一套：只覆盖当天展示，不影响其余 6 天的复用账本 */
  async function handleSwapDay(date: string) {
    const base = days.find((d) => d.date === date)
    if (!base || swapping) return
    const next = ((batches[date] ?? 0) + 1) % MAX_DAY_BATCH
    setSwapping(date)
    try {
      const result = await getWeekOutfit(city || undefined, date, next)
      if (!result || !('outfit_items' in result)) {
        toast.error('换一套失败，请稍后重试')
        return
      }
      const day = result as DailyOutfit
      setOverrides((prev) => ({
        ...prev,
        [date]: {
          ...base,
          outfit_items: day.outfit_items,
          completeness: day.completeness,
          match_score: day.match_score,
          reasoning: day.reasoning,
        },
      }))
      setBatches((prev) => ({ ...prev, [date]: next }))
    } finally {
      setSwapping(null)
    }
  }

  /** 生成一周穿搭海报（服务端 Pillow 渲染，base64 预览） */
  async function handleCreatePoster() {
    if (!days.length || posterLoading) return
    setPosterLoading(true)
    try {
      const res = await postWeekPoster({
        days: visibleDays.map((d) => ({
          date: d.date,
          weekday: d.weekday,
          weather: d.weather,
          temp_min: d.temp_min,
          temp_max: d.temp_max,
          lucky_elements: d.lucky_elements,
          items: (d.outfit_items || []).slice(0, 3).map((i) => ({
            name: i.name,
            category: i.category,
            image_url: i.image_url,
            primary_element: i.primary_element,
          })),
        })),
        theme: elementToTheme(days[0]?.lucky_elements?.[0] || ''),
        username: user?.nickname || user?.phone || '',
        city: week?.city,
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

  if (!isAuthenticated) return null

  const active = visibleDays.find((d) => d.date === expanded) || null

  // 首次加载：骨架；加载完仍无数据则整块静默隐藏，不打扰首页主流程
  if (loading && !days.length) {
    return (
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-[var(--brand-border)]/40 mb-4">
        <div className="flex items-center gap-2 mb-3">
          <CalendarRange className="w-4 h-4 text-[var(--wuxing-wood)]" />
          <span className="text-sm font-semibold text-[var(--brand-heading)]">一周穿搭</span>
        </div>
        <div className="flex gap-2 overflow-hidden">
          {Array.from({ length: 7 }).map((_, i) => (
            <div
              key={i}
              className="w-[74px] h-[132px] flex-shrink-0 rounded-xl bg-[var(--brand-surface)]/70 animate-pulse"
            />
          ))}
        </div>
      </div>
    )
  }

  if (!days.length) return null

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="bg-white rounded-2xl shadow-sm border border-[var(--brand-border)]/40 overflow-hidden mb-4"
      >
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[var(--wuxing-wood)]/20 to-[var(--wuxing-water)]/20 flex items-center justify-center">
              <CalendarRange className="w-4 h-4 text-[var(--wuxing-wood)]" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[var(--brand-heading)]">一周穿搭</h3>
              <p className="text-[10px] text-[var(--brand-subtle)] leading-tight">
                {week?.city || '本地'} · 按每天天气与运势预先排好
              </p>
            </div>
          </div>
          <motion.button
            whileTap={{ scale: 0.9, rotate: 180 }}
            onClick={fetchWeek}
            disabled={loading}
            className="w-7 h-7 rounded-lg bg-[var(--brand-surface)] flex items-center justify-center hover:bg-[var(--brand-surface-active)] transition-colors disabled:opacity-50"
            aria-label="重算一周穿搭"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[var(--brand-subtle)] ${loading ? 'animate-spin' : ''}`} />
          </motion.button>
        </div>

        {/* 7 列日历：移动端横向滚动 + 吸附 */}
        <div className="px-4 pb-2 flex gap-2 overflow-x-auto snap-x snap-mandatory scrollbar-hide">
          {visibleDays.map((day) => {
            const isOpen = expanded === day.date
            return (
              <button
                key={day.date}
                onClick={() => setExpanded(isOpen ? null : day.date)}
                aria-expanded={isOpen}
                aria-label={`${day.weekday} ${day.date} 的穿搭`}
                className={`snap-start flex-shrink-0 w-[74px] rounded-xl border px-1.5 py-2 text-left transition-colors ${
                  isOpen
                    ? 'border-[var(--wuxing-wood)]/50 bg-[var(--wuxing-wood)]/5'
                    : 'border-[var(--brand-border)]/60 bg-[var(--brand-surface)]/40 hover:bg-[var(--brand-surface-active)]/60'
                }`}
              >
                <p className="text-[10px] text-[var(--brand-subtle)] leading-none">{shortDate(day.date)}</p>
                <p
                  className={`text-xs font-medium mt-1 leading-none ${
                    day.date === today ? 'text-[var(--wuxing-wood)]' : 'text-[var(--brand-heading)]'
                  }`}
                >
                  {day.date === today ? '今天' : day.weekday}
                </p>
                <DayWeather day={day} />
                <DayThumbs items={day.outfit_items} />
                <p className="text-[10px] text-[var(--brand-subtle)] mt-1 leading-none">
                  {day.match_score > 0 ? `${day.match_score}分` : '—'}
                </p>
              </button>
            )
          })}
        </div>

        {/* 展开当日整套 */}
        <AnimatePresence initial={false}>
          {active && (
            <motion.div
              key={active.date}
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
              className="overflow-hidden"
            >
              <div className="px-4 py-3 mt-1 border-t border-[var(--brand-border)]/50 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs text-[var(--brand-body)]">
                    {active.date} {active.weekday}
                    {active.temp_min != null && active.temp_max != null && (
                      <span className="text-[var(--brand-subtle)]">
                        {' '}· {active.temp_min}~{active.temp_max}°C {active.weather}
                      </span>
                    )}
                  </p>
                  <div className="flex items-center gap-1.5">
                    {active.lucky_elements.slice(0, 2).map((el) => (
                      <span
                        key={el}
                        className="text-[10px] px-1.5 py-0.5 rounded-full font-medium text-white"
                        style={{ backgroundColor: ELEMENT_COLORS[el] || getWuxingConfig(el).color }}
                      >
                        {el}
                      </span>
                    ))}
                    <motion.button
                      whileTap={{ scale: 0.9 }}
                      onClick={() => handleSwapDay(active.date)}
                      disabled={swapping === active.date}
                      className="flex items-center gap-1 text-[11px] px-2 py-1 rounded-lg bg-[var(--brand-surface)] text-[var(--brand-subtle)] hover:bg-[var(--brand-surface-active)] transition-colors disabled:opacity-50"
                    >
                      <RefreshCw className={`w-3 h-3 ${swapping === active.date ? 'animate-spin' : ''}`} />
                      换一套
                    </motion.button>
                  </div>
                </div>

                <p className="text-xs text-[var(--brand-body)] leading-relaxed line-clamp-2">{active.reasoning}</p>

                <OutfitPiecesView
                  items={active.outfit_items}
                  missing={active.completeness?.missing ?? []}
                  luckyElement={active.lucky_elements?.[0]}
                  onSelectItem={setSelectedItem}
                  onFillMissing={handleFillMissing}
                  thumbSize="sm"
                />

                {/* 日记按天唯一且只记今天，未来日期列不做落库 */}
                {active.date === today && active.outfit_items.length > 0 && (
                  <motion.button
                    whileTap={{ scale: 0.98 }}
                    onClick={() =>
                      handleWearToday(active.outfit_items.map((i) => ({ id: i.id, category: i.category })))
                    }
                    disabled={logging}
                    className={`w-full py-2.5 rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${
                      logged
                        ? 'bg-emerald-50 text-emerald-600 border border-emerald-200 hover:bg-emerald-100'
                        : 'bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] text-white shadow-sm hover:opacity-95 disabled:opacity-60'
                    }`}
                  >
                    {logged ? (
                      <>
                        <Check className="w-4 h-4" /> 今日已记入 · 去日记
                      </>
                    ) : logging ? (
                      '记录中...'
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" /> 今天就穿它
                      </>
                    )}
                  </motion.button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 底部：一周海报入口 */}
        <div className="px-4 pb-4 pt-1">
          <button
            onClick={handleCreatePoster}
            disabled={posterLoading}
            className="w-full py-2.5 rounded-xl text-sm font-medium border border-[var(--brand-border)]/70 bg-[var(--brand-surface)]/50 text-[var(--brand-body)] hover:bg-[var(--brand-surface-active)]/60 transition-colors flex items-center justify-center gap-1.5 disabled:opacity-60"
          >
            <ImageIcon className="w-4 h-4" />
            {posterLoading ? '海报生成中...' : '生成一周穿搭海报'}
          </button>
        </div>
      </motion.div>

      {/* 单品详情（复用今日穿搭卡的弹窗） */}
      {selectedItem && (
        <ItemDetailModal
          item={{
            item_code: String(selectedItem.id),
            name: selectedItem.name,
            category: selectedItem.category || '',
            primary_element: selectedItem.primary_element || '',
            secondary_element: selectedItem.secondary_element,
            image_url: selectedItem.image_url,
            final_score: selectedItem.match_score,
          }}
          onClose={() => setSelectedItem(null)}
        />
      )}

      {/* 海报预览：移动端可长按保存，桌面端显式下载 */}
      {posterUrl && (
        <ImageLightbox
          imageUrl={posterUrl}
          alt="一周穿搭海报"
          caption="长按图片可保存 · 下载后即可分享"
          onClose={() => setPosterUrl(null)}
          actions={
            <a
              href={posterUrl}
              download="一周穿搭海报.png"
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

// ── 列内小元件 ────────────────────────────────────────────────────────────────

function DayWeather({ day }: { day: WeekOutfitDay }) {
  const Icon = weatherIconOf(day.weather || '')
  const hasRange = day.temp_min != null && day.temp_max != null
  return (
    <div className="mt-1.5 flex flex-col items-center gap-0.5">
      <Icon className="w-4 h-4 text-[var(--wuxing-water)]" />
      <span className="text-[9px] text-[var(--brand-subtle)] leading-none">
        {hasRange ? `${day.temp_min}~${day.temp_max}°` : '—'}
      </span>
    </div>
  )
}

function DayThumbs({ items }: { items: DailyOutfitItem[] }) {
  const shown = (items || []).slice(0, 3)
  return (
    <div className="mt-1.5 flex flex-col gap-1">
      {shown.map((item) => (
        <div key={item.id} className="w-full h-[26px] rounded-md overflow-hidden bg-[var(--brand-surface)] relative">
          {item.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={getImageUrl(item.image_url)}
              alt={item.name}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          ) : (
            <span className="absolute inset-0 flex items-center justify-center text-[9px] text-[var(--brand-subtle)]/60">
              {item.category || '单品'}
            </span>
          )}
          {item.primary_element && (
            <span
              className="absolute left-0.5 top-0.5 w-1.5 h-1.5 rounded-full"
              style={{
                backgroundColor: ELEMENT_COLORS[item.primary_element] || getWuxingConfig(item.primary_element).color,
              }}
            />
          )}
        </div>
      ))}
      {!shown.length && <span className="text-[9px] text-[var(--brand-subtle)] text-center">待补</span>}
    </div>
  )
}
