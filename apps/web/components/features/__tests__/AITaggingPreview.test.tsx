import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { AITaggingPreview } from '../AITaggingPreview'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

let mockStoreData: any = {}
const mockFetchTaggingPreview = vi.fn()
const mockClearTaggingPreview = vi.fn()

vi.mock('@/store/wardrobe', () => ({
  useWardrobeStore: () => mockStoreData,
}))

describe('AITaggingPreview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    mockStoreData = {
      taggingPreview: null,
      isTaggingLoading: false,
      fetchTaggingPreview: mockFetchTaggingPreview,
      clearTaggingPreview: mockClearTaggingPreview,
    }
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should return null when description is empty', () => {
    const { container } = render(<AITaggingPreview description="" />)
    expect(container.innerHTML).toBe('')
  })

  it('should return null when description is too short', () => {
    const { container } = render(<AITaggingPreview description="a" />)
    expect(container.innerHTML).toBe('')
  })

  it('should render AI detection header', async () => {
    vi.useRealTimers()
    const { container } = render(<AITaggingPreview description="白色棉质T恤" />)
    await waitFor(() => {
      expect(container.querySelector('.mt-4')).toBeInTheDocument()
    })
    expect(screen.getByText('AI 检测结果')).toBeInTheDocument()
  })

  it('should call fetchTaggingPreview after debounce', async () => {
    vi.useRealTimers()
    render(<AITaggingPreview description="白色棉质T恤" />)
    await waitFor(() => {
      expect(mockFetchTaggingPreview).toHaveBeenCalledWith('白色棉质T恤')
    })
  })

  it('should clear tagging preview when description is too short', async () => {
    vi.useRealTimers()
    render(<AITaggingPreview description="白" />)
    await waitFor(() => {
      expect(mockClearTaggingPreview).toHaveBeenCalled()
    })
  })

  it('should show loading indicator when isTaggingLoading is true', async () => {
    vi.useRealTimers()
    mockStoreData.isTaggingLoading = true
    const { container } = render(<AITaggingPreview description="白色棉质T恤" />)
    await waitFor(() => {
      expect(container.querySelector('.border-2.border-stone-300')).toBeInTheDocument()
    })
  })

  it('should render tagging result when available', async () => {
    vi.useRealTimers()
    mockStoreData.taggingPreview = {
      primary_element: '金',
      color: '白色',
      material: '棉',
      style: '休闲',
      season: ['春', '秋'],
      tags: ['简约', '日常'],
      confidence: 0.95,
    }
    const { container } = render(<AITaggingPreview description="白色棉质T恤" />)
    await waitFor(() => {
      expect(screen.getByText('主五行')).toBeInTheDocument()
    })
    expect(screen.getByText('白色')).toBeInTheDocument()
    expect(screen.getByText('棉')).toBeInTheDocument()
    expect(screen.getByText('休闲')).toBeInTheDocument()
    expect(screen.getByText('春')).toBeInTheDocument()
    expect(screen.getByText('秋')).toBeInTheDocument()
    expect(screen.getByText('简约')).toBeInTheDocument()
    expect(screen.getByText('95%')).toBeInTheDocument()
  })

  it('should call onTaggingComplete when result is available', async () => {
    vi.useRealTimers()
    const mockOnTaggingComplete = vi.fn()
    mockStoreData.taggingPreview = {
      primary_element: '木',
      color: '绿色',
    }
    render(<AITaggingPreview description="绿色衬衫" onTaggingComplete={mockOnTaggingComplete} />)
    await waitFor(() => {
      expect(mockOnTaggingComplete).toHaveBeenCalledWith({
        primary_element: '木',
        color: '绿色',
      })
    })
  })

  it('should render element emoji for known elements', async () => {
    vi.useRealTimers()
    mockStoreData.taggingPreview = {
      primary_element: '木',
      color: '绿色',
    }
    render(<AITaggingPreview description="绿色衬衫" />)
    await waitFor(() => {
      expect(screen.getByText(/🌿/)).toBeInTheDocument()
    })
  })

  it('should render default emoji for unknown elements', async () => {
    vi.useRealTimers()
    mockStoreData.taggingPreview = {
      primary_element: '未知',
      color: '红色',
    }
    render(<AITaggingPreview description="红色衣服" />)
    await waitFor(() => {
      expect(screen.getByText(/🔮/)).toBeInTheDocument()
    })
  })

  it('should show loading dots when isTaggingLoading', async () => {
    vi.useRealTimers()
    mockStoreData.isTaggingLoading = true
    const { container } = render(<AITaggingPreview description="白色棉质T恤" />)
    await waitFor(() => {
      const dots = container.querySelectorAll('.rounded-full.bg-amber-400')
      expect(dots.length).toBe(3)
    })
  })
})
