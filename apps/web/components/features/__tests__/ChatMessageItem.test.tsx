import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ChatMessageItem } from '../ChatMessageItem'
import { useChatStore } from '@/store/chat'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
}))

vi.mock('lucide-react', () => ({
  Sparkles: () => <span data-testid="sparkles-icon" />,
  // ChatMessageItem 引入 Toast 单例，Toast 依赖以下图标
  CheckCircle: () => <span data-testid="check-circle" />,
  AlertCircle: () => <span data-testid="alert-circle" />,
  Info: () => <span data-testid="info-icon" />,
  X: () => <span data-testid="x-icon" />,
}))

vi.mock('../RecommendCard', () => ({
  RecommendCard: ({ item, onImageClick }: any) => (
    <div data-testid={`recommend-card-${item.item_code}`}>
      <span>{item.name}</span>
      <button onClick={() => onImageClick('test-image-url')}>click image</button>
    </div>
  ),
}))

vi.mock('../PosterGenerator', () => ({
  PosterGenerator: ({ isOpen, onClose }: any) =>
    isOpen ? (
      <div data-testid="poster-generator">
        <button onClick={onClose}>close poster</button>
      </div>
    ) : null,
}))

vi.mock('../ImageLightbox', () => ({
  ImageLightbox: ({ imageUrl, onClose }: any) => (
    <div data-testid="image-lightbox">
      <span>{imageUrl}</span>
      <button onClick={onClose}>close lightbox</button>
    </div>
  ),
}))

vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}))

describe('ChatMessageItem', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render user message', () => {
    const message = {
      id: '1',
      role: 'user',
      content: 'Hello world',
      type: 'done',
    }
    render(<ChatMessageItem message={message as any} />)
    expect(screen.getByText('Hello world')).toBeInTheDocument()
    expect(screen.getByText('我')).toBeInTheDocument()
  })

  it('should render assistant message', () => {
    const message = {
      id: '2',
      role: 'assistant',
      content: 'Hi there',
      type: 'done',
    }
    render(<ChatMessageItem message={message as any} />)
    expect(screen.getByText('Hi there')).toBeInTheDocument()
    expect(screen.getByText('AI')).toBeInTheDocument()
  })

  it('should show loading dots for initial streaming message', () => {
    const message = {
      id: '3',
      role: 'assistant',
      content: '',
      type: 'streaming',
    }
    render(<ChatMessageItem message={message as any} />)
    expect(screen.getByText('正在分析您的八字和场景...')).toBeInTheDocument()
  })

  it('should show matching status when has analysis but no items', () => {
    const message = {
      id: '4',
      role: 'assistant',
      content: '',
      type: 'streaming',
      metadata: { targetElements: ['木', '火'] },
    }
    render(<ChatMessageItem message={message as any} />)
    expect(screen.getByText('正在为您匹配最合适的衣物...')).toBeInTheDocument()
  })

  it('should show generating status when has items', () => {
    const message = {
      id: '5',
      role: 'assistant',
      content: '',
      type: 'streaming',
      metadata: {
        targetElements: ['木'],
        items: [{ name: 'T恤', item_code: 'item1' }],
      },
    }
    render(<ChatMessageItem message={message as any} />)
    expect(screen.getByText('正在生成搭配建议...')).toBeInTheDocument()
  })

  it('should render element tags', () => {
    const message = {
      id: '6',
      role: 'assistant',
      content: 'Here is your recommendation',
      type: 'done',
      metadata: { targetElements: ['木', '火'] },
    }
    render(<ChatMessageItem message={message as any} />)
    expect(screen.getByText(/木/)).toBeInTheDocument()
    expect(screen.getByText(/火/)).toBeInTheDocument()
  })

  it('should render recommend cards when items exist', () => {
    const message = {
      id: '7',
      role: 'assistant',
      content: 'Recommendation',
      type: 'done',
      metadata: {
        items: [
          { name: 'T恤', item_code: 'item1' },
          { name: '裤子', item_code: 'item2' },
        ],
      },
    }
    render(<ChatMessageItem message={message as any} />)
    expect(screen.getByTestId('recommend-card-item1')).toBeInTheDocument()
    expect(screen.getByTestId('recommend-card-item2')).toBeInTheDocument()
  })

  it('should show poster generation button when items exist', () => {
    const message = {
      id: '8',
      role: 'assistant',
      content: 'Recommendation',
      type: 'done',
      metadata: {
        items: [{ name: 'T恤', item_code: 'item1' }],
      },
    }
    render(<ChatMessageItem message={message as any} />)
    expect(screen.getByText('生成分享海报')).toBeInTheDocument()
  })

  it('should NOT render wardrobe navigate button (去衣橱试搭已彻底移除)', () => {
    const message = {
      id: '8b',
      role: 'assistant',
      content: 'Recommendation',
      type: 'done',
      metadata: {
        items: [{ name: 'T恤', item_code: 'item1' }],
      },
    }
    render(<ChatMessageItem message={message as any} onNavigateToWardrobe={() => {}} />)
    expect(screen.queryByText('去衣橱试搭')).not.toBeInTheDocument()
  })

  it('should render wardrobe-sourced card after slot replaced (store replaceMessageItem)', () => {
    useChatStore.setState({
      conversations: [{
        id: 'conv_test', title: 't', createdAt: 0, updatedAt: 0,
        messages: [{
          id: 'msg_rep', role: 'assistant', content: 'x', type: 'done', createdAt: 0,
          metadata: { items: [{ name: 'T恤', item_code: 'item1', category: '上装', primary_element: '木', final_score: 0.9 }] },
        }],
      }],
      currentConversationId: 'conv_test',
    })
    // 模拟一次衣橱相似款原位替换
    useChatStore.getState().replaceMessageItem('conv_test', 'msg_rep', 'item1', {
      item_code: 'wardrobe-101', name: '米白T恤', category: '上装', primary_element: '木', final_score: 0.9, source: 'wardrobe',
    })
    const replacedItem = useChatStore.getState().conversations[0].messages[0].metadata!.items![0]
    const message = {
      id: 'msg_rep',
      role: 'assistant',
      content: 'x',
      type: 'done',
      metadata: { items: [replacedItem] },
    }
    render(<ChatMessageItem message={message as any} />)
    // 替换后槽位保留、来源变为衣橱（卡片 key 用新 item_code）
    expect(screen.getByTestId('recommend-card-wardrobe-101')).toBeInTheDocument()
    expect(screen.getByText('米白T恤')).toBeInTheDocument()
    useChatStore.setState({ conversations: [], currentConversationId: null, currentConversation: null })
  })

  it('should open poster when button is clicked', () => {
    const message = {
      id: '9',
      role: 'assistant',
      content: 'Recommendation',
      type: 'done',
      metadata: {
        items: [{ name: 'T恤', item_code: 'item1' }],
      },
    }
    render(<ChatMessageItem message={message as any} />)
    fireEvent.click(screen.getByText('生成分享海报'))
    expect(screen.getByTestId('poster-generator')).toBeInTheDocument()
  })

  it('should call onOpenPoster when poster is opened', () => {
    const mockOnOpenPoster = vi.fn()
    const message = {
      id: '10',
      role: 'assistant',
      content: 'Recommendation',
      type: 'done',
      metadata: {
        items: [{ name: 'T恤', item_code: 'item1' }],
      },
    }
    render(<ChatMessageItem message={message as any} onOpenPoster={mockOnOpenPoster} />)
    fireEvent.click(screen.getByText('生成分享海报'))
    expect(mockOnOpenPoster).toHaveBeenCalled()
  })

  it('should close poster and call onClosePoster', () => {
    vi.useFakeTimers()
    const mockOnClosePoster = vi.fn()
    const message = {
      id: '11',
      role: 'assistant',
      content: 'Recommendation',
      type: 'done',
      metadata: {
        items: [{ name: 'T恤', item_code: 'item1' }],
      },
    }
    render(<ChatMessageItem message={message as any} onClosePoster={mockOnClosePoster} />)
    fireEvent.click(screen.getByText('生成分享海报'))
    fireEvent.click(screen.getByText('close poster'))
    vi.advanceTimersByTime(200)
    expect(mockOnClosePoster).toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('should open image lightbox when image is clicked', () => {
    const message = {
      id: '12',
      role: 'assistant',
      content: 'Recommendation',
      type: 'done',
      metadata: {
        items: [{ name: 'T恤', item_code: 'item1' }],
      },
    }
    render(<ChatMessageItem message={message as any} />)
    fireEvent.click(screen.getByText('click image'))
    expect(screen.getByTestId('image-lightbox')).toBeInTheDocument()
  })

  it('should close image lightbox', () => {
    const message = {
      id: '13',
      role: 'assistant',
      content: 'Recommendation',
      type: 'done',
      metadata: {
        items: [{ name: 'T恤', item_code: 'item1' }],
      },
    }
    render(<ChatMessageItem message={message as any} />)
    fireEvent.click(screen.getByText('click image'))
    expect(screen.getByTestId('image-lightbox')).toBeInTheDocument()
    fireEvent.click(screen.getByText('close lightbox'))
    expect(screen.queryByTestId('image-lightbox')).not.toBeInTheDocument()
  })

  it('should show streaming cursor when streaming with content', () => {
    const message = {
      id: '14',
      role: 'assistant',
      content: 'Partial content',
      type: 'streaming',
    }
    const { container } = render(<ChatMessageItem message={message as any} />)
    expect(container.querySelector('.animate-pulse.align-middle')).toBeInTheDocument()
  })

  it('should not show streaming cursor when done', () => {
    const message = {
      id: '15',
      role: 'assistant',
      content: 'Final content',
      type: 'done',
    }
    const { container } = render(<ChatMessageItem message={message as any} />)
    expect(container.querySelector('.animate-pulse.align-middle')).not.toBeInTheDocument()
  })
})
