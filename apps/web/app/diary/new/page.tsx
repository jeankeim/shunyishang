'use client'

import { Suspense, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { DiaryForm } from '@/components/features/diary/DiaryForm'
import { useDiaryStore } from '@/store/diary'

// 内部组件：使用 useSearchParams，需被 Suspense 包裹
function NewDiaryContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const dateParam = searchParams.get('date')
  const { createNewDiary, isLoading, error, clearError } = useDiaryStore()

  useEffect(() => {
    return () => clearError()
  }, [clearError])

  const handleSubmit = async (data: {
    diary_date: string
    mood?: string
    occasion?: string
    notes?: string
    rating?: number
    image_urls?: string[]
    items?: { item_source: string; wardrobe_item_id?: number }[]
    trigger_ai_review?: boolean
  }) => {
    const diary = await createNewDiary({
      diary_date: data.diary_date,
      mood: data.mood,
      occasion: data.occasion,
      notes: data.notes,
      rating: data.rating,
      image_urls: data.image_urls,
      items: data.items,
      trigger_ai_review: data.trigger_ai_review,
    })
    router.push('/diary')
  }

  return (
    <div className="max-w-lg mx-auto">
      {/* 头部 */}
      <div className="flex items-center gap-3 mb-5">
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={() => router.back()}
          className="p-2 rounded-lg hover:bg-stone-100 text-stone-500 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </motion.button>
        <div>
          <h1 className="text-xl font-bold text-stone-800">新建日记</h1>
          <p className="text-xs text-stone-500">记录今日穿搭与心情</p>
        </div>
      </div>

      {/* 表单卡片 */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
        <DiaryForm
          initialData={dateParam ? { diary_date: dateParam } : undefined}
          onSubmit={handleSubmit}
          onCancel={() => router.back()}
        />
      </div>

      {error && (
        <div className="mt-4 bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-600">
          {error}
        </div>
      )}
    </div>
  )
}

export default function NewDiaryPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-lg mx-auto">
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100 animate-pulse">
            <div className="h-4 bg-stone-200 rounded mb-4 w-1/3" />
            <div className="h-32 bg-stone-100 rounded" />
          </div>
        </div>
      }
    >
      <NewDiaryContent />
    </Suspense>
  )
}
