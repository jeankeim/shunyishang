'use client'

/**
 * 个人备案版：会员页面已禁用，自动跳转到首页
 */
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function MembershipPage() {
  const router = useRouter()

  useEffect(() => {
    router.replace('/')
  }, [router])

  return null
}
