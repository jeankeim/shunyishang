import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { RecommendCard } from '../RecommendCard'
import type { RecommendItem } from '@/types'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, onClick, ...props }: any) => <div onClick={onClick} {...props}>{children}</div>,
    button: ({ children, onClick, ...props }: any) => <button onClick={onClick} {...props}>{children}</button>,
    svg: ({ children, ...props }: any) => <svg {...props}>{children}</svg>,
    path: (props: any) => <path {...props} />,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

// Mock API
vi.mock('@/lib/api', () => ({
  submitFeedback: vi.fn().mockResolvedValue(undefined),
  cancelFeedback: vi.fn().mockResolvedValue(undefined),
  reportBehavior: vi.fn().mockResolvedValue(undefined),
}))

// Mock wuxing-config
vi.mock('@/lib/wuxing-config', () => ({
  getWuxingConfig: (element: string) => ({
    element,
    emoji: '🌱',
    gradientClass: 'from-green-400 to-green-600',
    bgClass: 'bg-green-100',
    textClass: 'text-green-700',
  }),
}))

// Mock image
vi.mock('@/lib/image', () => ({
  getImageUrl: (url: string) => url,
}))

const mockItem: RecommendItem = {
  item_id: 1,
  item_code: 'ITEM001',
  name: '绿色棉质T恤',
  category: '上衣',
  primary_element: '木',
  color: '绿色',
  image_url: 'http://example.com/image.jpg',
  thumbnail_url: undefined,
  source: 'public',
  final_score: 0.85,
  semantic_score: 0.8,
  wuxing_score: 0.9,
  scene_score: 0.7,
  reason: '五行属木，适合今日穿搭',
}

describe('RecommendCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render item name', () => {
    render(<RecommendCard item={mockItem} index={0} />)
    expect(screen.getByText('绿色棉质T恤')).toBeInTheDocument()
  })

  it('should render item category', () => {
    render(<RecommendCard item={mockItem} index={0} />)
    expect(screen.getByText('上衣')).toBeInTheDocument()
  })

  it('should render item color', () => {
    render(<RecommendCard item={mockItem} index={0} />)
    expect(screen.getByText('颜色：绿色')).toBeInTheDocument()
  })

  it('should render final score as percentage', () => {
    render(<RecommendCard item={mockItem} index={0} />)
    expect(screen.getByText('85%')).toBeInTheDocument()
  })

  it('should render reason text', () => {
    render(<RecommendCard item={mockItem} index={0} />)
    expect(screen.getByText('五行属木，适合今日穿搭')).toBeInTheDocument()
  })

  it('should render primary element badge', () => {
    render(<RecommendCard item={mockItem} index={0} />)
    expect(screen.getByText('木')).toBeInTheDocument()
  })

  it('should render public library tag', () => {
    render(<RecommendCard item={mockItem} index={0} />)
    expect(screen.getByText('📚 公共库')).toBeInTheDocument()
  })

  it('should render wardrobe tag for wardrobe items', () => {
    const item: RecommendItem = { ...mockItem, source: 'wardrobe' }
    render(<RecommendCard item={item} index={0} />)
    expect(screen.getByText('🏠 自有')).toBeInTheDocument()
  })

  it('should render image when image_url is present', () => {
    render(<RecommendCard item={mockItem} index={0} />)
    // The image is rendered as a background-image style
    const imageDiv = document.querySelector('[style*="example.com"]')
    expect(imageDiv).toBeInTheDocument()
  })

  it('should render placeholder when no image_url', () => {
    const item = { ...mockItem, image_url: '' }
    render(<RecommendCard item={item} index={0} />)
    expect(screen.getByText('🌱')).toBeInTheDocument()
  })

  it('should call onFeedback when like button is clicked via detail modal', async () => {
    const onFeedback = vi.fn()
    render(<RecommendCard item={mockItem} index={0} onFeedback={onFeedback} />)
    
    // 点击图片显示覆盖层
    const imageDiv = document.querySelector('[style*="example.com"]')
    fireEvent.click(imageDiv!)
    
    // 点击喜欢按钮
    const likeBtn = screen.getByLabelText('喜欢这个推荐')
    fireEvent.click(likeBtn)
    
    await waitFor(() => {
      expect(onFeedback).toHaveBeenCalledWith('like')
    })
  })

  it('should expand details when chevron is clicked', () => {
    render(<RecommendCard item={mockItem} index={0} />)
    
    const expandBtn = screen.getByLabelText('展开详情')
    fireEvent.click(expandBtn)
    
    expect(screen.getByText('语义匹配')).toBeInTheDocument()
    expect(screen.getByText('五行匹配')).toBeInTheDocument()
    expect(screen.getByText('场景适配')).toBeInTheDocument()
  })

  it('should show score bars in details', () => {
    render(<RecommendCard item={mockItem} index={0} />)
    fireEvent.click(screen.getByLabelText('展开详情'))
    
    // Semantic score 80%
    expect(screen.getAllByText('80%').length).toBeGreaterThan(0)
    // Wuxing score 90%
    expect(screen.getAllByText('90%').length).toBeGreaterThan(0)
    // Scene score 70%
    expect(screen.getAllByText('70%').length).toBeGreaterThan(0)
  })

  it('should show like/dislike in detail modal when image is clicked', () => {
    render(<RecommendCard item={mockItem} index={0} />)
    
    const imageDiv = document.querySelector('[style*="example.com"]')
    fireEvent.click(imageDiv!)
    
    expect(screen.getByLabelText('喜欢这个推荐')).toBeInTheDocument()
    expect(screen.getByLabelText('不喜欢这个推荐')).toBeInTheDocument()
    expect(screen.getByText('喜欢')).toBeInTheDocument()
    expect(screen.getByText('不喜欢')).toBeInTheDocument()
  })

  it('should not show scene score when scene_score is 0 or undefined', () => {
    const item = { ...mockItem, scene_score: 0 }
    render(<RecommendCard item={item} index={0} />)
    fireEvent.click(screen.getByLabelText('展开详情'))
    
    expect(screen.queryByText('场景适配')).not.toBeInTheDocument()
  })

  it('should open detail modal when card image is clicked (no on-card overlay)', () => {
    render(<RecommendCard item={mockItem} index={0} />)

    // 卡片上不再有独立的「查看大图」放大镜按钮
    expect(screen.queryByLabelText('查看大图')).not.toBeInTheDocument()
    // 未点图前，反馈按钮不在卡片上
    expect(screen.queryByLabelText('喜欢这个推荐')).not.toBeInTheDocument()

    // 点击图片 → 打开放大详情弹窗（弹窗含「综合匹配度」与反馈栏）
    const imageDiv = document.querySelector('[style*="example.com"]')
    fireEvent.click(imageDiv!)
    expect(screen.getByText('综合匹配度')).toBeInTheDocument()
    expect(screen.getByLabelText('喜欢这个推荐')).toBeInTheDocument()
  })

  it('should show undo option after feedback is given (in detail modal)', async () => {
    render(<RecommendCard item={mockItem} index={0} />)

    // 点击图片 → 打开放大详情弹窗，反馈操作栏在弹窗内
    const imageDiv = document.querySelector('[style*="example.com"]')
    fireEvent.click(imageDiv!)

    const likeBtn = screen.getByLabelText('喜欢这个推荐')
    fireEvent.click(likeBtn)

    // 提交成功后：喜欢按钮消失，短暂动画后切到「已喜欢 + 撤销」
    await waitFor(() => {
      expect(screen.queryByLabelText('喜欢这个推荐')).not.toBeInTheDocument()
    }, { timeout: 1500 })
    await waitFor(() => {
      expect(screen.getByText('撤销')).toBeInTheDocument()
    }, { timeout: 1500 })
    expect(screen.getByText('已喜欢')).toBeInTheDocument()
  })

  it('should show dislike reasons with multi-select when dislike button is clicked', () => {
    render(<RecommendCard item={mockItem} index={0} />)
    
    // 点击图片显示覆盖层
    const imageDiv = document.querySelector('[style*="example.com"]')
    fireEvent.click(imageDiv!)
    
    // 点击不喜欢
    const dislikeBtn = screen.getByLabelText('不喜欢这个推荐')
    fireEvent.click(dislikeBtn)
    
    // 应显示多选原因选项
    expect(screen.getByText('不喜欢的原因？（可多选）')).toBeInTheDocument()
    expect(screen.getByText('风格不符')).toBeInTheDocument()
    expect(screen.getByText('颜色不喜欢')).toBeInTheDocument()
    expect(screen.getByText('不适合场景')).toBeInTheDocument()
    expect(screen.getByText('太厚/太薄')).toBeInTheDocument()
    expect(screen.getByText('其他')).toBeInTheDocument()
    // 确认按钮初始禁用
    expect(screen.getByText('确认')).toBeInTheDocument()
  })

  it('should support multi-select for dislike reasons', () => {
    render(<RecommendCard item={mockItem} index={0} />)
    
    const imageDiv = document.querySelector('[style*="example.com"]')
    fireEvent.click(imageDiv!)
    fireEvent.click(screen.getByLabelText('不喜欢这个推荐'))
    
    // 点击多个原因
    fireEvent.click(screen.getByText('风格不符'))
    fireEvent.click(screen.getByText('颜色不喜欢'))
    
    // 选中状态显示 ✓ 前缀
    expect(screen.getByText('✓ 风格不符')).toBeInTheDocument()
    expect(screen.getByText('✓ 颜色不喜欢')).toBeInTheDocument()
    // 确认按钮显示选中数量
    expect(screen.getByText('确认(2)')).toBeInTheDocument()
  })
})
