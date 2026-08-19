'use client'

/**
 * 后台管理 - 用户大模型调用明细
 *
 * 按用户分组展示每日大模型使用情况：用户信息（ID/昵称/注册时间/城市）
 * + 调用详情（日期/场景/查询词/结果摘要/模型与 token 用量/调用成本）。
 * 成本按 DashScope 官网单价由 token 用量折算，历史数据按场景平均 token 估算。
 * 仅统计真实大模型调用（缓存命中不记录）。
 * 默认近 7 天，支持单日筛选与按用户搜索。
 */

import { useEffect, useState } from 'react'
import { getAdminLlmUsage, type AdminLlmUsageResponse } from '@/lib/api'

const RANGE_OPTIONS = [7, 14, 30]

const SCENE_LABELS: Record<string, { label: string; cls: string }> = {
  agent: { label: '推荐 Agent', cls: 'bg-primary/10 text-primary' },
  fortune: { label: '每日运势', cls: 'bg-amber-50 text-amber-600' },
  fortune_report: { label: '年度报告', cls: 'bg-violet-50 text-violet-600' },
  wardrobe_ai: { label: '衣橱 AI 打标', cls: 'bg-blue-50 text-blue-600' },
  diary_ai: { label: '日记 AI 分析', cls: 'bg-pink-50 text-pink-600' },
}

function SceneBadge({ scene }: { scene: string }) {
  const meta = SCENE_LABELS[scene] ?? { label: scene, cls: 'bg-gray-100 text-gray-500' }
  return (
    <span className={`inline-block px-2 py-0.5 rounded-md text-xs whitespace-nowrap ${meta.cls}`}>
      {meta.label}
    </span>
  )
}

function formatTime(iso: string | null): string {
  if (!iso) return '-'
  // 2026-08-18T10:00:00+00:00 → 08-18 10:00
  return iso.slice(5, 16).replace('T', ' ')
}

function formatCost(cost: number): string {
  return `¥${(cost || 0).toFixed(4)}`
}

export default function AdminLlmUsagePage() {
  const [days, setDays] = useState(7)
  const [date, setDate] = useState('')
  const [keyword, setKeyword] = useState('')
  const [query, setQuery] = useState('')
  const [data, setData] = useState<AdminLlmUsageResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // 搜索词防抖
  useEffect(() => {
    const t = setTimeout(() => setQuery(keyword.trim()), 300)
    return () => clearTimeout(t)
  }, [keyword])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    getAdminLlmUsage({ days, date: date || undefined, q: query || undefined })
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : '加载失败')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [days, date, query])

  return (
    <div className="space-y-6">
      {/* 标题 + 筛选 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-800">用户大模型调用明细</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            按用户分组 · 仅统计真实大模型调用（缓存命中不计）
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="搜索昵称 / 用户ID"
            className="h-8 px-3 text-xs bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary/40 w-36"
          />
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="h-8 px-2 text-xs bg-white border border-gray-200 rounded-lg text-gray-600 focus:outline-none focus:ring-1 focus:ring-primary/40"
          />
          {date && (
            <button
              onClick={() => setDate('')}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              清除日期
            </button>
          )}
          <div className="flex items-center gap-1 bg-white border border-gray-200 rounded-lg p-1">
            {RANGE_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => {
                  setDays(d)
                  setDate('')
                }}
                className={`px-3 py-1 rounded-md text-xs transition-colors ${
                  !date && days === d
                    ? 'bg-primary text-white'
                    : 'text-gray-500 hover:bg-gray-100'
                }`}
              >
                近{d}天
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-100 text-red-600 text-sm rounded-xl px-4 py-3">
          {error}
        </div>
      )}

      {loading && !data ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-32 bg-white rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : data ? (
        <>
          {/* 汇总卡片 */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
              <p className="text-xs text-gray-400">调用次数</p>
              <p className="text-2xl font-semibold mt-1.5 text-primary">
                {data.totals.call_count}
              </p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
              <p className="text-xs text-gray-400">调用用户数</p>
              <p className="text-2xl font-semibold mt-1.5 text-blue-600">
                {data.totals.user_count}
              </p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
              <p className="text-xs text-gray-400">调用成本（元）</p>
              <p className="text-2xl font-semibold mt-1.5 text-amber-600">
                {formatCost(data.totals.cost)}
              </p>
            </div>
          </div>

          <p className="text-xs text-gray-400 -mt-2">
            统计范围 {data.range.start} ~ {data.range.end}
            · 成本按 DashScope 官网单价由 token 用量折算（历史数据按场景平均 token 估算）
          </p>

          {data.users.length === 0 ? (
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-10 text-center">
              <p className="text-sm text-gray-400">该时间范围内暂无大模型调用记录</p>
            </div>
          ) : (
            data.users.map((u) => (
              <section
                key={u.user_id}
                className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5"
              >
                {/* 用户信息头 */}
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mb-4">
                  <span className="text-sm font-semibold text-gray-800">{u.nickname}</span>
                  <span className="text-xs text-gray-400">ID {u.user_id}</span>
                  {u.city && <span className="text-xs text-gray-400">城市 {u.city}</span>}
                  {u.created_at && (
                    <span className="text-xs text-gray-400">
                      注册 {u.created_at.slice(0, 10)}
                    </span>
                  )}
                  <span className="ml-auto text-xs text-gray-500">
                    {u.call_count} 次调用 · {formatCost(u.cost)}
                  </span>
                </div>

                {/* 调用明细表 */}
                <div className="overflow-x-auto">
                  <table className="w-full text-xs min-w-[720px]">
                    <thead>
                      <tr className="text-gray-400 border-b border-gray-100">
                        <th className="text-left font-normal py-2 pr-3">时间</th>
                        <th className="text-left font-normal py-2 pr-3">场景</th>
                        <th className="text-left font-normal py-2 pr-3">查询词</th>
                        <th className="text-left font-normal py-2 pr-3">结果摘要</th>
                        <th className="text-right font-normal py-2 pl-3">调用成本</th>
                      </tr>
                    </thead>
                    <tbody className="text-gray-600">
                      {u.records.map((r) => (
                        <tr key={r.id} className="border-b border-gray-50 last:border-0">
                          <td className="py-2.5 pr-3 whitespace-nowrap text-gray-400">
                            {formatTime(r.created_at)}
                          </td>
                          <td className="py-2.5 pr-3">
                            <SceneBadge scene={r.scene} />
                            {r.model && (
                              <p className="text-[10px] text-gray-300 mt-1 whitespace-nowrap">
                                {r.model} · 入{r.input_tokens ?? 0}/出{r.output_tokens ?? 0}
                              </p>
                            )}
                          </td>
                          <td className="py-2.5 pr-3 max-w-[220px] truncate" title={r.query_text || ''}>
                            {r.query_text || '-'}
                          </td>
                          <td className="py-2.5 pr-3 max-w-[280px] truncate" title={r.result_summary || ''}>
                            {r.result_summary || '-'}
                          </td>
                          <td className="py-2.5 pl-3 text-right whitespace-nowrap">
                            {r.cost > 0 ? formatCost(r.cost) : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ))
          )}
        </>
      ) : null}
    </div>
  )
}
