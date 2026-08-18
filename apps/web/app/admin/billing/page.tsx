'use client'

/**
 * 后台管理 - 阿里云费用消耗账单
 *
 * 数据来源：后端每日 00:35 通过阿里云 BSS OpenAPI（QueryAccountBill 按天粒度）
 * 拉取全产品账单（ECS/RDS/OSS/CDN/百炼大模型等）落库，支持手动同步。
 * 注意：阿里云当天账单通常次日才出全，最新数据截至昨日。
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  getAdminBills,
  syncAdminBills,
  type AdminBillsResponse,
} from '@/lib/api'

const RANGE_OPTIONS = [31, 90, 180]

// 产品代码 → 友好简称（未命中时显示后端返回的产品名）
const PRODUCT_SHORT_NAMES: Record<string, string> = {
  ecs: '云服务器 ECS',
  rds: '云数据库 RDS',
  oss: '对象存储 OSS',
  cdn: 'CDN',
  dashscope: '百炼大模型',
  sls: '日志服务 SLS',
  redis: '云数据库 Redis',
  eip: '弹性公网 IP',
  disk: '云盘',
  domain: '域名',
}

function formatMoney(n: number): string {
  return `¥${(n ?? 0).toFixed(2)}`
}

export default function AdminBillingPage() {
  const [days, setDays] = useState(31)
  const [data, setData] = useState<AdminBillsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = useCallback(async (d: number) => {
    setLoading(true)
    setError('')
    try {
      const res = await getAdminBills(d)
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

  const handleSync = async () => {
    setSyncing(true)
    setNotice('')
    try {
      const res = await syncAdminBills(3)
      setNotice(
        res.errors.length > 0
          ? `同步完成（${res.synced_days} 天），部分失败: ${res.errors.join('；')}`
          : `同步完成：${res.synced_days} 天，共 ${res.synced_rows} 条产品账单`
      )
      await load(days)
    } catch (e) {
      setNotice(e instanceof Error ? e.message : '同步失败')
    } finally {
      setSyncing(false)
    }
  }

  const chartData = (data?.daily ?? []).map((d) => ({
    ...d,
    label: d.date.slice(5),
  }))
  const dailyAvg =
    data && days > 0 ? data.total_pretax / days : 0

  return (
    <div className="space-y-6">
      {/* 标题 + 操作区 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-800">阿里云费用消耗账单</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            按天自动更新（每日 00:35 同步）· 覆盖 ECS / RDS / OSS / CDN / 大模型等全部产品
          </p>
        </div>
        <div className="flex items-center gap-2">
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
          <button
            onClick={handleSync}
            disabled={syncing || data?.configured === false}
            className="px-3 py-1.5 rounded-lg text-xs bg-primary text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
          >
            {syncing ? '同步中…' : '手动同步'}
          </button>
        </div>
      </div>

      {notice && (
        <div className="bg-blue-50 border border-blue-100 text-blue-600 text-sm rounded-xl px-4 py-3">
          {notice}
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-100 text-red-600 text-sm rounded-xl px-4 py-3">
          {error}
        </div>
      )}

      {/* 未配置 AK 提示 */}
      {data && !data.configured && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl px-5 py-4">
          <p className="text-sm font-medium text-amber-800">尚未接入阿里云账单数据</p>
          <p className="text-xs text-amber-700 mt-1.5 leading-relaxed">
            请在后端 .env 配置具备账单只读权限的 AccessKey 后重启服务：
            <code className="block mt-2 bg-amber-100/60 rounded-lg px-3 py-2 font-mono">
              ALIYUN_BILLING_ACCESS_KEY_ID=xxx<br />
              ALIYUN_BILLING_ACCESS_KEY_SECRET=xxx
            </code>
            <span className="block mt-1.5">
              建议在阿里云 RAM 创建子账号，仅授予 AliyunBSSReadOnlyAccess 权限。
              配置完成后服务启动时会自动回填最近 30 天账单。
            </span>
          </p>
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
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <SummaryCard label={`近${days}天总费用（应付）`} value={formatMoney(data.total_pretax)} accent="text-primary" />
            <SummaryCard label="现金支付" value={formatMoney(data.total_payment)} accent="text-gray-800" />
            <SummaryCard label="日均费用" value={formatMoney(dailyAvg)} accent="text-blue-600" />
            <SummaryCard label="涉及产品数" value={`${data.by_product.length} 个`} accent="text-violet-600" />
          </div>

          {/* 每日费用趋势 */}
          <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
            <h2 className="text-sm font-medium text-gray-700 mb-4">每日费用趋势（应付金额）</h2>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} minTickGap={20} />
                  <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} width={56} tickFormatter={(v: number) => `¥${v}`} />
                  <Tooltip
                    formatter={(value) => [formatMoney(Number(value)), '应付金额']}
                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  />
                  <Bar dataKey="pretax_amount" fill="#3DA35D" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* 按产品分类明细 */}
          <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 overflow-x-auto">
            <h2 className="text-sm font-medium text-gray-700 mb-4">按产品分类明细</h2>
            {data.by_product.length === 0 ? (
              <p className="text-sm text-gray-400 py-6 text-center">
                {data.configured ? '统计区间内暂无账单数据' : '待配置账单 AK 后自动同步'}
              </p>
            ) : (
              <table className="w-full text-xs min-w-[640px]">
                <thead>
                  <tr className="text-gray-400 border-b border-gray-100">
                    <th className="text-left font-normal py-2 pr-3">产品</th>
                    <th className="text-right font-normal py-2 px-3">应付金额</th>
                    <th className="text-right font-normal py-2 px-3">现金支付</th>
                    <th className="text-right font-normal py-2 px-3">优惠抵扣</th>
                    <th className="text-right font-normal py-2 pl-3 w-1/4">占比</th>
                  </tr>
                </thead>
                <tbody className="text-gray-600">
                  {data.by_product.map((p) => (
                    <tr key={p.product_code} className="border-b border-gray-50 last:border-0">
                      <td className="py-2.5 pr-3">
                        <span className="font-medium text-gray-700">
                          {PRODUCT_SHORT_NAMES[p.product_code] || p.product_name || p.product_code}
                        </span>
                        <span className="text-gray-300 ml-1.5">{p.product_code}</span>
                      </td>
                      <td className="text-right px-3 font-medium">{formatMoney(p.pretax_amount)}</td>
                      <td className="text-right px-3">{formatMoney(p.payment_amount)}</td>
                      <td className="text-right px-3">{formatMoney(p.deducted_by_coupons)}</td>
                      <td className="pl-3">
                        <div className="flex items-center justify-end gap-2">
                          <div className="flex-1 max-w-[120px] h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary rounded-full"
                              style={{ width: `${Math.min(p.percentage, 100)}%` }}
                            />
                          </div>
                          <span className="w-10 text-right text-gray-500">{p.percentage}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {/* 同步状态说明 */}
          <p className="text-xs text-gray-400">
            最后同步时间：{data.last_sync_at ? data.last_sync_at.replace('T', ' ').slice(0, 19) : '尚未同步'}
             · 阿里云账单存在约 1 天延迟，最新数据截至昨日；每日自动回刷最近 3 天以覆盖延迟更新。
          </p>
        </>
      ) : null}
    </div>
  )
}

function SummaryCard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`text-xl font-semibold mt-1.5 ${accent}`}>{value}</p>
    </div>
  )
}
