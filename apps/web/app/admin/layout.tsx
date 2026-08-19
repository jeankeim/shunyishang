'use client'

/**
 * 后台管理布局
 *
 * 鉴权守卫：调用 /api/v1/admin/me 判断管理员身份（环境变量白名单）。
 * - 未登录 → 提示登录
 * - 非管理员 → 提示无权限
 * 本模块对 C 端不可见：不进入底部导航/Header，仅 URL 直达。
 */

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { getAdminStatus, initAuthToken } from '@/lib/api'

type GuardState = 'loading' | 'unauthorized' | 'forbidden' | 'ok'

const NAV_ITEMS = [
  { href: '/admin', label: '运营数据看板', exact: true },
  { href: '/admin/billing', label: '阿里云费用账单', exact: false },
  { href: '/admin/llm-usage', label: '大模型调用明细', exact: false },
]

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [state, setState] = useState<GuardState>('loading')
  const [nickname, setNickname] = useState('')

  useEffect(() => {
    let cancelled = false
    initAuthToken()
    getAdminStatus()
      .then((res) => {
        if (cancelled) return
        setNickname(res.nickname)
        setState(res.is_admin ? 'ok' : 'forbidden')
      })
      .catch(() => {
        if (!cancelled) setState('unauthorized')
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (state === 'loading') {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-sm text-gray-400">正在验证管理员身份…</p>
      </main>
    )
  }

  if (state === 'unauthorized' || state === 'forbidden') {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center px-6">
        <div className="max-w-sm w-full bg-white rounded-2xl border border-gray-100 shadow-sm p-8 text-center">
          <div className="text-3xl mb-3">{state === 'unauthorized' ? '🔒' : '⛔'}</div>
          <h1 className="text-base font-semibold text-gray-800 mb-2">
            {state === 'unauthorized' ? '请先登录' : '无管理员权限'}
          </h1>
          <p className="text-sm text-gray-500 leading-relaxed">
            {state === 'unauthorized'
              ? '后台管理模块需要登录后访问。'
              : '当前账号不在管理员白名单中，如需授权请联系管理员配置 ADMIN_USER_CODES。'}
          </p>
          <Link
            href="/"
            className="inline-block mt-5 text-sm text-primary hover:underline"
          >
            返回首页
          </Link>
        </div>
      </main>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-gray-800">后台管理</span>
              <nav className="flex items-center gap-1">
                {NAV_ITEMS.map((item) => {
                  const active = item.exact
                    ? pathname === item.href
                    : pathname.startsWith(item.href)
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                        active
                          ? 'bg-primary/10 text-primary font-medium'
                          : 'text-gray-500 hover:text-gray-800 hover:bg-gray-100'
                      }`}
                    >
                      {item.label}
                    </Link>
                  )
                })}
              </nav>
            </div>
            <div className="flex items-center gap-3">
              {nickname && <span className="text-xs text-gray-400">{nickname}</span>}
              <Link href="/" className="text-xs text-gray-400 hover:text-gray-600">
                返回前台 →
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6">{children}</main>
    </div>
  )
}
