import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MobileControlPanel } from '../MobileControlPanel'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

vi.mock('lucide-react', () => ({
  ChevronDown: () => <span data-testid="chevron-down" />,
  ChevronUp: () => <span data-testid="chevron-up" />,
}))

vi.mock('../FiveElementList', () => ({
  FiveElementList: () => <div data-testid="five-element-list" />,
}))

vi.mock('../BaziCard', () => ({
  BaziCard: ({ onEdit }: any) => (
    <div data-testid="bazi-card">
      <button onClick={onEdit}>edit</button>
    </div>
  ),
}))

vi.mock('../BaziInputSection', () => ({
  BaziInputSection: () => <div data-testid="bazi-input-section" />,
}))

vi.mock('../WeatherSceneSection', () => ({
  WeatherSceneSection: ({ onSceneChange }: any) => (
    <div data-testid="weather-scene-section">
      <button data-testid="pick-scene" onClick={() => onSceneChange?.('商务', '金', '商务办公')}>选场景</button>
      <button data-testid="clear-scene" onClick={() => onSceneChange?.('', '', '')}>取消场景</button>
    </div>
  ),
}))

let mockChatStore: any = {}
let mockUserStore: any = {}

vi.mock('@/store/chat', () => ({
  useChatStore: () => mockChatStore,
}))

vi.mock('@/store/user', () => ({
  useUserStore: () => mockUserStore,
}))

describe('MobileControlPanel', () => {
  const mockOnSceneChange = vi.fn()
  const mockOnWeatherChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockChatStore = {
      radarData: { currentData: [], suggestedData: [], xiyongShen: [] },
      setUserBazi: vi.fn(),
    }
    mockUserStore = {
      user: null,
      isAuthenticated: false,
    }
  })

  it('should render expand button', () => {
    render(<MobileControlPanel onSceneChange={mockOnSceneChange} onWeatherChange={mockOnWeatherChange} />)
    expect(screen.getByText('展开设置')).toBeInTheDocument()
  })

  it('should show ChevronUp when collapsed', () => {
    render(<MobileControlPanel onSceneChange={mockOnSceneChange} onWeatherChange={mockOnWeatherChange} />)
    expect(screen.getByTestId('chevron-up')).toBeInTheDocument()
  })

  it('should expand and show content when clicked', () => {
    render(<MobileControlPanel onSceneChange={mockOnSceneChange} onWeatherChange={mockOnWeatherChange} />)
    fireEvent.click(screen.getByText('展开设置'))
    expect(screen.getByText('收起设置')).toBeInTheDocument()
    expect(screen.getByTestId('chevron-down')).toBeInTheDocument()
  })

  it('should show BaziInputSection when not authenticated', () => {
    render(<MobileControlPanel onSceneChange={mockOnSceneChange} onWeatherChange={mockOnWeatherChange} />)
    fireEvent.click(screen.getByText('展开设置'))
    expect(screen.getByTestId('bazi-input-section')).toBeInTheDocument()
  })

  it('should show BaziCard when authenticated with bazi', () => {
    mockUserStore = {
      user: { bazi: { year: '1990', month: '1', day: '1', hour: '12' } },
      isAuthenticated: true,
    }
    render(<MobileControlPanel onSceneChange={mockOnSceneChange} onWeatherChange={mockOnWeatherChange} />)
    fireEvent.click(screen.getByText('展开设置'))
    expect(screen.getByTestId('bazi-card')).toBeInTheDocument()
  })

  it('should show FiveElementList when no bazi', () => {
    render(<MobileControlPanel onSceneChange={mockOnSceneChange} onWeatherChange={mockOnWeatherChange} />)
    fireEvent.click(screen.getByText('展开设置'))
    expect(screen.getByTestId('five-element-list')).toBeInTheDocument()
  })

  it('should not show FiveElementList when has bazi', () => {
    mockUserStore = {
      user: { bazi: { year: '1990', month: '1', day: '1', hour: '12' } },
      isAuthenticated: true,
    }
    render(<MobileControlPanel onSceneChange={mockOnSceneChange} onWeatherChange={mockOnWeatherChange} />)
    fireEvent.click(screen.getByText('展开设置'))
    expect(screen.queryByTestId('five-element-list')).not.toBeInTheDocument()
  })

  it('should show WeatherSceneSection when expanded', () => {
    render(<MobileControlPanel onSceneChange={mockOnSceneChange} onWeatherChange={mockOnWeatherChange} />)
    fireEvent.click(screen.getByText('展开设置'))
    expect(screen.getByTestId('weather-scene-section')).toBeInTheDocument()
  })

  it('should show bazi hint when has bazi', () => {
    mockUserStore = {
      user: { bazi: { year: '1990', month: '1', day: '1', hour: '12' } },
      isAuthenticated: true,
    }
    render(<MobileControlPanel onSceneChange={mockOnSceneChange} onWeatherChange={mockOnWeatherChange} />)
    fireEvent.click(screen.getByText('展开设置'))
    expect(screen.getByText(/基于您的八字分析/)).toBeInTheDocument()
  })

  it('should collapse when clicked again', () => {
    render(<MobileControlPanel onSceneChange={mockOnSceneChange} onWeatherChange={mockOnWeatherChange} />)
    fireEvent.click(screen.getByText('展开设置'))
    expect(screen.getByText('收起设置')).toBeInTheDocument()
    fireEvent.click(screen.getByText('收起设置'))
    expect(screen.getByText('展开设置')).toBeInTheDocument()
  })

  it('should auto-collapse and forward selection when scene picked', () => {
    render(<MobileControlPanel onSceneChange={mockOnSceneChange} onWeatherChange={mockOnWeatherChange} />)
    fireEvent.click(screen.getByText('展开设置'))
    fireEvent.click(screen.getByTestId('pick-scene'))
    // 场景透传给父级，且面板自动收起（避免遮挡推荐输入框）
    expect(mockOnSceneChange).toHaveBeenCalledWith('商务', '金', '商务办公')
    expect(screen.getByText('展开设置')).toBeInTheDocument()
    expect(screen.queryByTestId('weather-scene-section')).not.toBeInTheDocument()
  })

  it('should stay expanded when scene cleared', () => {
    render(<MobileControlPanel onSceneChange={mockOnSceneChange} onWeatherChange={mockOnWeatherChange} />)
    fireEvent.click(screen.getByText('展开设置'))
    fireEvent.click(screen.getByTestId('clear-scene'))
    expect(mockOnSceneChange).toHaveBeenCalledWith('', '', '')
    expect(screen.getByText('收起设置')).toBeInTheDocument()
  })
})
