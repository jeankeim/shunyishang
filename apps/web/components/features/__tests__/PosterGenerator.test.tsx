import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { PosterGenerator } from '../PosterGenerator'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, onClick, ...props }: any) => <div onClick={onClick} {...props}>{children}</div>,
    button: ({ children, onClick, ...props }: any) => <button onClick={onClick} {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Download: () => <span data-testid="download-icon" />,
  Share2: () => <span data-testid="share-icon" />,
  Sparkles: () => <span data-testid="sparkles-icon" />,
  X: () => <span data-testid="x-icon" />,
  Palette: () => <span data-testid="palette-icon" />,
  Edit3: () => <span data-testid="edit-icon" />,
}))

// Mock react-dom createPortal
vi.mock('react-dom', () => ({
  createPortal: (node: any) => node,
}))

// Mock PosterTemplate and PosterTemplateSelector
vi.mock('../PosterTemplate', () => ({
  PosterTemplate: ({ title, items }: any) => (
    <div data-testid="poster-template">
      <span>{title}</span>
      <span>{items.length} items</span>
    </div>
  ),
  PosterTemplateSelector: ({ selectedTemplate, onSelect }: any) => (
    <div data-testid="poster-template-selector">
      <button onClick={() => onSelect('wuxing')} data-testid="select-wuxing">wuxing</button>
      <button onClick={() => onSelect('card')} data-testid="select-card">card</button>
      <span data-testid="current-template">{selectedTemplate}</span>
    </div>
  ),
}))

// Mock PosterEditor
vi.mock('../PosterEditor', () => ({
  PosterEditor: ({ title, onTitleChange }: any) => (
    <div data-testid="poster-editor">
      <input value={title} onChange={(e) => onTitleChange(e.target.value)} data-testid="title-input" />
    </div>
  ),
}))

// Mock usePoster hook
const mockPoster = {
  posterRef: { current: null },
  title: '测试标题',
  setTitle: vi.fn(),
  quote: '测试文案',
  setQuote: vi.fn(),
  signature: '测试签名',
  setSignature: vi.fn(),
  selectedTemplate: 'simple',
  setSelectedTemplate: vi.fn(),
  selectedTheme: { name: '木', primary: '#3DA35D', secondary: '#4A90C4' },
  setSelectedTheme: vi.fn(),
  items: [{ name: 'T恤', primary_element: '木' }],
  xiyongElements: ['木', '火'],
  scene: '日常',
  download: vi.fn(),
  share: vi.fn(),
  isGenerating: false,
  error: null as string | null,
}

vi.mock('@/hooks/usePoster', () => ({
  usePoster: () => mockPoster,
}))

const mockItems = [
  { name: 'T恤', image_url: 'http://example.com/1.jpg', primary_element: '木' },
  { name: '裤子', image_url: 'http://example.com/2.jpg', primary_element: '水' },
]

describe('PosterGenerator', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockPoster.error = null
    mockPoster.isGenerating = false
  })

  it('should return null when closed', () => {
    const { container } = render(
      <PosterGenerator isOpen={false} onClose={vi.fn()} items={mockItems} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('should render dialog title when open', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    expect(screen.getByText('生成分享海报')).toBeInTheDocument()
  })

  it('should render subtitle text', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    expect(screen.getByText('选择模板，编辑内容，一键分享')).toBeInTheDocument()
  })

  it('should render close button', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    expect(screen.getByLabelText('关闭海报生成器')).toBeInTheDocument()
  })

  it('should call onClose when close button is clicked', () => {
    const onClose = vi.fn()
    render(<PosterGenerator isOpen={true} onClose={onClose} items={mockItems} />)
    fireEvent.click(screen.getByLabelText('关闭海报生成器'))
    expect(onClose).toHaveBeenCalled()
  })

  it('should render template and edit tabs', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    expect(screen.getByText('选择模板')).toBeInTheDocument()
    expect(screen.getByText('编辑内容')).toBeInTheDocument()
  })

  it('should show template selector by default', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    expect(screen.getByTestId('poster-template-selector')).toBeInTheDocument()
  })

  it('should switch to edit tab when clicked', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    fireEvent.click(screen.getByText('编辑内容'))
    expect(screen.getByTestId('poster-editor')).toBeInTheDocument()
  })

  it('should switch back to template tab when clicked', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    fireEvent.click(screen.getByText('编辑内容'))
    fireEvent.click(screen.getByText('选择模板'))
    expect(screen.getByTestId('poster-template-selector')).toBeInTheDocument()
  })

  it('should render download button', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    expect(screen.getByLabelText('下载高清海报')).toBeInTheDocument()
  })

  it('should render share button', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    expect(screen.getByLabelText('分享到社交平台')).toBeInTheDocument()
  })

  it('should call download when download button is clicked', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    fireEvent.click(screen.getByLabelText('下载高清海报'))
    expect(mockPoster.download).toHaveBeenCalled()
  })

  it('should call share when share button is clicked', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    fireEvent.click(screen.getByLabelText('分享到社交平台'))
    expect(mockPoster.share).toHaveBeenCalled()
  })

  it('should show generating state', () => {
    mockPoster.isGenerating = true
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    expect(screen.getByText('生成中...')).toBeInTheDocument()
    expect(screen.getByLabelText('正在生成海报')).toBeDisabled()
  })

  it('should show error message when error exists', () => {
    mockPoster.error = '生成失败'
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    expect(screen.getByText('生成失败')).toBeInTheDocument()
  })

  it('should disable buttons when generating', () => {
    mockPoster.isGenerating = true
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    expect(screen.getByLabelText('正在生成海报')).toBeDisabled()
    expect(screen.getByLabelText('分享到社交平台')).toBeDisabled()
  })

  it('should render poster template preview', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    // PosterTemplate is rendered in the preview area
    expect(screen.getAllByTestId('poster-template').length).toBeGreaterThanOrEqual(1)
  })

  it('should toggle preview on mobile', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    const toggleBtn = screen.getByLabelText(/海报预览/)
    fireEvent.click(toggleBtn)
  })

  it('should pass items to poster template', () => {
    render(<PosterGenerator isOpen={true} onClose={vi.fn()} items={mockItems} />)
    // The mocked PosterTemplate shows item count
    expect(screen.getAllByText(/items/).length).toBeGreaterThanOrEqual(1)
  })
})
