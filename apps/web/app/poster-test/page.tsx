'use client'

import { useState } from 'react'
import { PosterGenerator } from '@/components/features/PosterGenerator'

export default function PosterTestPage() {
  const [isOpen, setIsOpen] = useState(false)

  // 测试数据
  const testItems = [
    {
      name: '红色真丝衬衫',
      image_url: '/uploads/wardrobe/1/image_001_红色真丝衬衫，光滑面料，优雅剪裁.jpg',
      primary_element: '火',
      color: '红色',
    },
    {
      name: '黑色西装裤',
      image_url: '/uploads/wardrobe/1/image_010_黑色西装裤，垂感面料，商务休闲.jpg',
      primary_element: '水',
      color: '黑色',
    },
    {
      name: '金色配饰项链',
      image_url: '/uploads/wardrobe/1/image_020_金色配饰，精致工艺.jpg',
      primary_element: '金',
      color: '金色',
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-50 flex items-center justify-center p-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">海报生成器测试</h1>
        <p className="text-gray-600 mb-8">点击按钮打开海报生成器</p>
        
        <button
          onClick={() => setIsOpen(true)}
          className="px-8 py-4 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl font-medium text-lg hover:from-purple-600 hover:to-pink-600 transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5"
        >
          打开海报生成器
        </button>

        <PosterGenerator
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          title="今日五行穿搭推荐"
          items={testItems}
          xiyongElements={['火', '木']}
          scene="商务会议"
          quote="火生土，今日事业运旺，适合重要会议和商务洽谈"
          username="测试用户"
        />
      </div>
    </div>
  )
}
