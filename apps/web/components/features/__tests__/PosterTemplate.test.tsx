import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { PosterTemplate, PosterTemplateSelector } from '../PosterTemplate'
import { WUXING_THEMES } from '@/lib/poster-templates'

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Sparkles: () => <span data-testid="sparkles" />,
  Stars: () => <span data-testid="stars" />,
  Smartphone: () => <span data-testid="smartphone" />,
}))

// Mock image
vi.mock('@/lib/image', () => ({
  getImageUrl: (url: string) => url,
}))

const mockTheme = WUXING_THEMES.wood || { name: '木', primary: '#3DA35D', secondary: '#4A90C4', text: '#fff', bg: '#000' }

const mockItems = [
  { name: 'T恤', image_url: 'http://example.com/1.jpg', primary_element: '木', color: '绿色' },
  { name: '裤子', image_url: 'http://example.com/2.jpg', primary_element: '水', color: '蓝色' },
  { name: '鞋子', image_url: undefined, primary_element: '火', color: '红色' },
]

const baseProps = {
  title: '今日五行穿搭推荐',
  items: mockItems,
  xiyongElements: ['木', '火'],
  scene: '日常',
  quote: '火生土，今日事业运旺',
  signature: '我的个人穿搭',
  theme: mockTheme,
  username: '测试用户',
}

describe('PosterTemplate', () => {
  describe('SimpleTemplate (layout="simple")', () => {
    it('should render title', () => {
      render(<PosterTemplate layout="simple" {...baseProps} />)
      expect(screen.getByText('今日五行穿搭推荐')).toBeInTheDocument()
    })

    it('should render quote', () => {
      render(<PosterTemplate layout="simple" {...baseProps} />)
      expect(screen.getByText(/火生土，今日事业运旺/)).toBeInTheDocument()
    })

    it('should render item names', () => {
      render(<PosterTemplate layout="simple" {...baseProps} />)
      expect(screen.getByText('T恤')).toBeInTheDocument()
      expect(screen.getByText('裤子')).toBeInTheDocument()
      expect(screen.getByText('鞋子')).toBeInTheDocument()
    })

    it('should render item sequence numbers', () => {
      render(<PosterTemplate layout="simple" {...baseProps} />)
      expect(screen.getByText('1')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
      expect(screen.getByText('3')).toBeInTheDocument()
    })

    it('should render without quote', () => {
      render(<PosterTemplate layout="simple" {...baseProps} quote={undefined} />)
      expect(screen.getByText('今日五行穿搭推荐')).toBeInTheDocument()
    })

    it('should render items without images', () => {
      render(<PosterTemplate layout="simple" {...baseProps} items={[{ name: '无图物品', primary_element: '金' }]} />)
      expect(screen.getByText('无图物品')).toBeInTheDocument()
    })
  })

  describe('WuxingTemplate (layout="wuxing")', () => {
    it('should render title', () => {
      render(<PosterTemplate layout="wuxing" {...baseProps} />)
      expect(screen.getByText('今日五行穿搭推荐')).toBeInTheDocument()
    })

    it('should render item names', () => {
      render(<PosterTemplate layout="wuxing" {...baseProps} />)
      expect(screen.getByText('T恤')).toBeInTheDocument()
      expect(screen.getByText('裤子')).toBeInTheDocument()
    })

    it('should render xiyong elements', () => {
      render(<PosterTemplate layout="wuxing" {...baseProps} />)
      // Elements should be rendered somewhere
      expect(screen.getAllByText('木').length).toBeGreaterThan(0)
    })

    it('should render wuxing subtitle', () => {
      render(<PosterTemplate layout="wuxing" {...baseProps} />)
      expect(screen.getByText('五行相生 · 运势亨通')).toBeInTheDocument()
    })

    it('should render scene', () => {
      render(<PosterTemplate layout="wuxing" {...baseProps} />)
      expect(screen.getAllByText(/日常/).length).toBeGreaterThan(0)
    })
  })

  describe('CardTemplate (layout="card")', () => {
    it('should render title', () => {
      render(<PosterTemplate layout="card" {...baseProps} />)
      expect(screen.getByText('今日五行穿搭推荐')).toBeInTheDocument()
    })

    it('should render item names', () => {
      render(<PosterTemplate layout="card" {...baseProps} />)
      expect(screen.getByText('T恤')).toBeInTheDocument()
      expect(screen.getByText('裤子')).toBeInTheDocument()
    })

    it('should render username', () => {
      render(<PosterTemplate layout="card" {...baseProps} />)
      expect(screen.getByText('@测试用户')).toBeInTheDocument()
    })

    it('should render signature', () => {
      render(<PosterTemplate layout="card" {...baseProps} />)
      expect(screen.getAllByText('我的个人穿搭').length).toBeGreaterThan(0)
    })
  })

  describe('Default layout', () => {
    it('should fall back to simple template for unknown layout', () => {
      render(<PosterTemplate layout={'unknown' as any} {...baseProps} />)
      expect(screen.getByText('今日五行穿搭推荐')).toBeInTheDocument()
      expect(screen.getByText('T恤')).toBeInTheDocument()
    })
  })

  describe('PosterTemplateSelector', () => {
    it('should render all three template options', () => {
      render(<PosterTemplateSelector selectedTemplate="simple" onSelect={vi.fn()} />)
      expect(screen.getByText('简约东方')).toBeInTheDocument()
      expect(screen.getByText('五行国潮')).toBeInTheDocument()
      // Card template name
      expect(screen.getByText(/卡片/)).toBeInTheDocument()
    })

    it('should render template descriptions', () => {
      render(<PosterTemplateSelector selectedTemplate="simple" onSelect={vi.fn()} />)
      expect(screen.getByText('现代极简，突出单品')).toBeInTheDocument()
      expect(screen.getByText('传统美学，文化底蕴')).toBeInTheDocument()
    })

    it('should mark selected template', () => {
      render(<PosterTemplateSelector selectedTemplate="wuxing" onSelect={vi.fn()} />)
      const wuxingBtn = screen.getByLabelText(/五行国潮/)
      expect(wuxingBtn).toHaveAttribute('aria-pressed', 'true')
    })

    it('should call onSelect when template is clicked', () => {
      const onSelect = vi.fn()
      render(<PosterTemplateSelector selectedTemplate="simple" onSelect={onSelect} />)
      fireEvent.click(screen.getByLabelText(/五行国潮/))
      expect(onSelect).toHaveBeenCalledWith('wuxing')
    })

    it('should show checkmark for selected template', () => {
      render(<PosterTemplateSelector selectedTemplate="simple" onSelect={vi.fn()} />)
      const simpleBtn = screen.getByLabelText(/简约东方/)
      expect(simpleBtn.querySelector('div')).toBeInTheDocument()
    })
  })
})
