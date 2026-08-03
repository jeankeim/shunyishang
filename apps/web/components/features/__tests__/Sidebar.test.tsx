import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Sidebar } from '../Sidebar'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, onClick, ...props }: any) => <div onClick={onClick} {...props}>{children}</div>,
    button: ({ children, onClick, ...props }: any) => <button onClick={onClick} {...props}>{children}</button>,
  },
}))

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Plus: () => <span data-testid="plus" />,
  MessageSquare: () => <span data-testid="msg-square" />,
  X: () => <span data-testid="x" />,
  Menu: () => <span data-testid="menu" />,
  Sparkles: () => <span data-testid="sparkles" />,
}))

// Configurable mock store
let mockStoreData: any = {}

vi.mock('@/store/chat', () => ({
  useChatStore: () => mockStoreData,
}))

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockStoreData = {
      conversations: [],
      currentConversationId: null,
      setCurrentConversation: vi.fn(),
      createConversation: vi.fn(),
    }
  })

  it('should return null when collapsed', () => {
    const { container } = render(<Sidebar collapsed={true} onToggle={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('should render sidebar content when expanded', () => {
    render(<Sidebar collapsed={false} onToggle={vi.fn()} />)
    expect(screen.getByText('历史记录')).toBeInTheDocument()
  })

  it('should render "新建对话" button when expanded', () => {
    render(<Sidebar collapsed={false} onToggle={vi.fn()} />)
    expect(screen.getByText('新建对话')).toBeInTheDocument()
  })

  it('should render "暂无历史记录" when no conversations', () => {
    render(<Sidebar collapsed={false} onToggle={vi.fn()} />)
    expect(screen.getByText('暂无历史记录')).toBeInTheDocument()
  })

  it('should render conversation titles when conversations exist', () => {
    mockStoreData.conversations = [
      { id: '1', title: '对话1' },
      { id: '2', title: '对话2' },
    ]
    render(<Sidebar collapsed={false} onToggle={vi.fn()} />)
    expect(screen.getByText('对话1')).toBeInTheDocument()
    expect(screen.getByText('对话2')).toBeInTheDocument()
  })

  it('should call createConversation and onToggle when new conversation button is clicked', () => {
    const onToggle = vi.fn()
    render(<Sidebar collapsed={false} onToggle={onToggle} />)
    fireEvent.click(screen.getByText('新建对话'))
    expect(mockStoreData.createConversation).toHaveBeenCalled()
    expect(onToggle).toHaveBeenCalled()
  })

  it('should call setCurrentConversation and onToggle when conversation is clicked', () => {
    mockStoreData.conversations = [
      { id: '1', title: '对话1' },
    ]
    const onToggle = vi.fn()
    render(<Sidebar collapsed={false} onToggle={onToggle} />)
    fireEvent.click(screen.getByText('对话1'))
    expect(mockStoreData.setCurrentConversation).toHaveBeenCalledWith('1')
    expect(onToggle).toHaveBeenCalled()
  })

  it('should call onToggle when close button is clicked', () => {
    const onToggle = vi.fn()
    render(<Sidebar collapsed={false} onToggle={onToggle} />)
    const closeBtn = screen.getByLabelText('关闭侧边栏')
    fireEvent.click(closeBtn)
    expect(onToggle).toHaveBeenCalled()
  })

  it('should render footer text', () => {
    render(<Sidebar collapsed={false} onToggle={vi.fn()} />)
    expect(screen.getByText('我的个人穿搭')).toBeInTheDocument()
  })

  it('should highlight current conversation', () => {
    mockStoreData.conversations = [
      { id: '1', title: '对话1' },
      { id: '2', title: '对话2' },
    ]
    mockStoreData.currentConversationId = '2'
    render(<Sidebar collapsed={false} onToggle={vi.fn()} />)
    const conv2Btn = screen.getByText('对话2').closest('button')
    expect(conv2Btn?.className).toContain('from-[var(--brand-surface)]')
  })
})
