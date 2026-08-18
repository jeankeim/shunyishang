'use client'

/**
 * 后台管理 - 产品运营数据看板
 *
 * 核心指标：DAU 及趋势；扩展指标：新增用户、推荐次数、接口调用量、
 * 日记数、运势查询数、点赞/点踩、新增衣橱衣物。
 * 数据来源：历史取每日聚合快照（定时任务 00:35 生成），当天实时计算。
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getAdminDashboard, type AdminDashboardResponse } from '@/lib/api'

const RANGE_OPTIONS = [7, 30, 90]

const TODAY_CARDS = [
  { key: 'dau', label: '今日活跃用户 DAU', accent: 'text-primary' },
  { key: 'new_users', label: '今日新增用户', accent: 'text-blue-600' },
  { key: 'recommend_count', label: '今日推荐次数', accent: 'text-amber-600' },
  { key: 'api_requests', label: '今日接口调用量', accent: 'text-violet-600' },
] as const

function formatNumber(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)}w`
  return String(n ?? 0)
}

export default function AdminDashboardPage() {
  const [days, setDays] = useState(30)
  const [data, setData] = useState<AdminDashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async (d: number) => {
    setLoading(true)
    setError('')
    try {
      const res = await getAdminDashboard(d)
      setData(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(days)
  }, [days, load])

  const trend = data?.trend ?? []
  // 图表横轴只展示 月-日
  const chartData = trend.map((t) => ({ ...t, label: t.date.slice(5) }))
  const recentTable = [...trend].slice(-7).reverse()

  return (
    <div className="space-y-6">
      {/* 标题 + 时间范围 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-800">产品运营数据看板</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            按天更新 · 历史数据每日 00:35 自动聚合，当天数据实时计算
          </p>
        </div>
        <div className="flex items-center gap-1 bg-white border border-gray-200 rounded-lg p-1">
          {RANGE_OPTIONS.map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1 rounded-md text-xs transition-colors ${
                days === d
                  ? 'bg-primary text-white'
                  : 'text-gray-500 hover:bg-gray-100'
              }`}
            >
              近{d}天
            </button>
          ))}
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
          {/* 今日核心指标卡 */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {TODAY_CARDS.map((card) => (
              <div
                key={card.key}
                className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4"
              >
                <p className="text-xs text-gray-400">{card.label}</p>
                <p className={`text-2xl font-semibold mt-1.5 ${card.accent}`}>
                  {formatNumber(data.today[card.key])}
                </p>
              </div>
            ))}
          </div>

          {/* 累计概况 */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm px-5 py-4 flex flex-wrap gap-x-8 gap-y-2">
            <SummaryItem label="累计注册用户" value={data.totals.total_users} />
            <SummaryItem label="用户衣橱物品" value={data.totals.total_wardrobe_items} />
            <SummaryItem label="公共种子库物品" value={data.totals.total_seed_items} />
            <SummaryItem label={`近${days}天推荐总量`} value={data.totals.recommend_total} />
            <SummaryItem label={`近${days}天接口调用`} value={data.totals.api_total} />
          </div>

          {/* DAU 趋势 */}
          <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
            <h2 className="text-sm font-medium text-gray-700 mb-4">
              每日活跃用户（DAU）趋势
            </h2>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -18, bottom: 0 }}>
                  <defs>
                    <linearGradient id="dauGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3DA35D" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#3DA35D" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} minTickGap={20} />
                  <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip
                    formatter={(value) => [value, 'DAU']}
                    labelFormatter={(label) => `日期: ${label}`}
                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  />
                  <Area
                    type="monotone"
                    dataKey="dau"
                    stroke="#3DA35D"
                    strokeWidth={2}
                    fill="url(#dauGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* 推荐次数 & 接口调用量 */}
          <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
            <h2 className="text-sm font-medium text-gray-700 mb-4">
              推荐次数与接口调用量
            </h2>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 5, right: 10, left: -18, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} minTickGap={20} />
                  <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="recommend_count" name="推荐次数" fill="#F59E0B" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="api_requests" name="接口调用量" fill="#8B5CF6" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* 近7天明细表 */}
          <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 overflow-x-auto">
            <h2 className="text-sm font-medium text-gray-700 mb-4">近 7 天指标明细</h2>
            <table className="w-full text-xs min-w-[720px]">
              <thead>
                <tr className="text-gray-400 border-b border-gray-100">
                  <th className="text-left font-normal py-2 pr-3">日期</th>
                  <th className="text-right font-normal py-2 px-3">DAU</th>
                  <th className="text-right font-normal py-2 px-3">新增用户</th>
                  <th className="text-right font-normal py-2 px-3">推荐次数</th>
                  <th className="text-right font-normal py-2 px-3">接口调用</th>
                  <th className="text-right font-normal py-2 px-3">日记</th>
                  <th className="text-right font-normal py-2 px-3">运势</th>
                  <th className="text-right font-normal py-2 px-3">点赞/点踩</th>
                  <th className="text-right font-normal py-2 pl-3">新增衣物</th>
                </tr>
              </thead>
              <tbody className="text-gray-600">
                {recentTable.map((row) => (
                  <tr key={row.date} className="border-b border-gray-50 last:border-0">
                    <td className="py-2.5 pr-3">{row.date}</td>
                    <td className="text-right px-3 font-medium text-primary">{row.dau}</td>
                    <td className="text-right px-3">{row.new_users}</td>
                    <td className="text-right px-3">{row.recommend_count}</td>
                    <td className="text-right px-3">{row.api_requests}</td>
                    <td className="text-right px-3">{row.diary_count}</td>
                    <td className="text-right px-3">{row.fortune_count}</td>
                    <td className="text-right px-3">
                      {row.like_count} / {row.dislike_count}
                    </td>
                    <td className="text-right pl-3">{row.wardrobe_added}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      ) : null}
    </div>
  )
}

function SummaryItem({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-gray-400">{label}</span>
      <span className="text-base font-semibold text-gray-800 mt-0.5">
        {formatNumber(value)}
      </span>
    </div>
  )
}
