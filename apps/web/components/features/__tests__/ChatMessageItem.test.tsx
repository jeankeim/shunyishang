import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ChatMessageItem } from '../ChatMessageItem'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
}))

vi.mock('lucide-react', () => ({
  Sparkles: () => <span data-testid="sparkles-icon" />,
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
