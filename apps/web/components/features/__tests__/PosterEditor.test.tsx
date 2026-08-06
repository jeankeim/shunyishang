import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { PosterEditor } from '../PosterEditor'
import { WUXING_THEMES } from '@/lib/poster-templates'

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Edit3: () => <span data-testid="edit-icon" />,
  Type: () => <span data-testid="type-icon" />,
  MessageSquare: () => <span data-testid="msg-icon" />,
  PenTool: () => <span data-testid="pen-icon" />,
  Palette: () => <span data-testid="palette-icon" />,
}))

const mockTheme = WUXING_THEMES.wood || { name: '木', primary: '#3DA35D', secondary: '#4A90C4' }

describe('PosterEditor', () => {
  const defaultProps = {
    title: '测试标题',
    onTitleChange: vi.fn(),
    quote: '测试文案',
    onQuoteChange: vi.fn(),
    signature: '测试签名',
    onSignatureChange: vi.fn(),
    theme: mockTheme,
    onThemeChange: vi.fn(),
  }

  it('should render title input with value', () => {
    render(<PosterEditor {...defaultProps} />)
    expect(screen.getByDisplayValue('测试标题')).toBeInTheDocument()
  })

  it('should render quote textarea with value', () => {
    render(<PosterEditor {...defaultProps} />)
    expect(screen.getByDisplayValue('测试文案')).toBeInTheDocument()
  })

  it('should render signature input with value', () => {
    render(<PosterEditor {...defaultProps} />)
    expect(screen.getByDisplayValue('测试签名')).toBeInTheDocument()
  })

  it('should render section labels', () => {
    render(<PosterEditor {...defaultProps} />)
    expect(screen.getByText('海报标题')).toBeInTheDocument()
    expect(screen.getByText('推荐文案')).toBeInTheDocument()
    expect(screen.getByText('个人签名')).toBeInTheDocument()
    expect(screen.getByText('配色主题')).toBeInTheDocument()
  })

  it('should render character count for title', () => {
    render(<PosterEditor {...defaultProps} />)
    expect(screen.getByText('4/50')).toBeInTheDocument()
  })

  it('should render character count for quote', () => {
    render(<PosterEditor {...defaultProps} />)
    expect(screen.getByText('4/200')).toBeInTheDocument()
  })

  it('should render character count for signature', () => {
    render(<PosterEditor {...defaultProps} />)
    expect(screen.getByText('4/30')).toBeInTheDocument()
  })

  it('should call onTitleChange when title is changed', () => {
    render(<PosterEditor {...defaultProps} />)
    const input = screen.getByDisplayValue('测试标题')
    fireEvent.change(input, { target: { value: '新标题' } })
    expect(defaultProps.onTitleChange).toHaveBeenCalledWith('新标题')
  })

  it('should call onQuoteChange when quote is changed', () => {
    render(<PosterEditor {...defaultProps} />)
    const textarea = screen.getByDisplayValue('测试文案')
    fireEvent.change(textarea, { target: { value: '新文案' } })
    expect(defaultProps.onQuoteChange).toHaveBeenCalledWith('新文案')
  })

  it('should call onSignatureChange when signature is changed', () => {
    render(<PosterEditor {...defaultProps} />)
    const input = screen.getByDisplayValue('测试签名')
    fireEvent.change(input, { target: { value: '新签名' } })
    expect(defaultProps.onSignatureChange).toHaveBeenCalledWith('新签名')
  })

  it('should render theme selector with radio group', () => {
    render(<PosterEditor {...defaultProps} />)
    expect(screen.getByRole('radiogroup')).toBeInTheDocument()
  })

  it('should render all five theme buttons', () => {
    render(<PosterEditor {...defaultProps} />)
    const radioButtons = screen.getAllByRole('radio')
    expect(radioButtons.length).toBeGreaterThanOrEqual(5)
  })

  it('should mark current theme as selected', () => {
    render(<PosterEditor {...defaultProps} />)
    const selectedBtn = screen.getByLabelText(`${mockTheme.name}主题`)
    expect(selectedBtn).toHaveAttribute('aria-checked', 'true')
  })

  it('should call onThemeChange when a different theme is clicked', () => {
    render(<PosterEditor {...defaultProps} />)
    const themeButtons = screen.getAllByRole('radio')
    // Click a non-selected theme
    const nonSelected = themeButtons.find(btn => btn.getAttribute('aria-checked') !== 'true')
    if (nonSelected) {
      fireEvent.click(nonSelected)
      expect(defaultProps.onThemeChange).toHaveBeenCalled()
    }
  })

  it('should render placeholders when values are empty', () => {
    render(
      <PosterEditor
        {...defaultProps}
        title=""
        quote=""
        signature=""
      />
    )
    expect(screen.getByPlaceholderText('例如：今日五行穿搭推荐')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('例如：火生土，今日事业运旺')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('例如：我的个人衣橱')).toBeInTheDocument()
  })
})
