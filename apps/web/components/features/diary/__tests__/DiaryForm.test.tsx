import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { DiaryForm } from '../DiaryForm'
import { useWardrobeStore } from '@/store/wardrobe'
import type { WardrobeItem } from '@/lib/api'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, onClick, type, disabled, ...props }: any) => (
      <button onClick={onClick} type={type} disabled={disabled} {...props}>{children}</button>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

describe('DiaryForm', () => {
  it('should render date picker with today as default', () => {
    render(<DiaryForm onSubmit={vi.fn()} />)
    const now = new Date()
    const expected = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日`
    expect(screen.getByText(expected)).toBeInTheDocument()
  })

  it('should render all mood options', () => {
    render(<DiaryForm onSubmit={vi.fn()} />)
    expect(screen.getByText('😊')).toBeInTheDocument()
    expect(screen.getByText('🤩')).toBeInTheDocument()
    expect(screen.getByText('😌')).toBeInTheDocument()
    expect(screen.getByText('😐')).toBeInTheDocument()
    expect(screen.getByText('😢')).toBeInTheDocument()
  })

  it('should render all occasion options', () => {
    render(<DiaryForm onSubmit={vi.fn()} />)
    expect(screen.getByText('日常')).toBeInTheDocument()
    expect(screen.getByText('上班')).toBeInTheDocument()
    expect(screen.getByText('约会')).toBeInTheDocument()
    expect(screen.getByText('聚会')).toBeInTheDocument()
    expect(screen.getByText('运动')).toBeInTheDocument()
    expect(screen.getByText('旅行')).toBeInTheDocument()
    expect(screen.getByText('正式场合')).toBeInTheDocument()
  })

  it('should render rating stars', () => {
    render(<DiaryForm onSubmit={vi.fn()} />)
    const stars = screen.getAllByText('★')
    expect(stars).toHaveLength(5)
  })

  it('should render notes textarea', () => {
    render(<DiaryForm onSubmit={vi.fn()} />)
    expect(screen.getByPlaceholderText('记录今天的穿搭心得...')).toBeInTheDocument()
  })

  it('should render submit button with "创建日记" text', () => {
    render(<DiaryForm onSubmit={vi.fn()} />)
    expect(screen.getByText('创建日记')).toBeInTheDocument()
  })

  it('should render submit button with "更新日记" text when isEdit is true', () => {
    render(<DiaryForm onSubmit={vi.fn()} isEdit />)
    expect(screen.getByText('更新日记')).toBeInTheDocument()
  })

  it('should render cancel button when onCancel is provided', () => {
    const onCancel = vi.fn()
    render(<DiaryForm onSubmit={vi.fn()} onCancel={onCancel} />)
    expect(screen.getByText('取消')).toBeInTheDocument()
  })

  it('should call onCancel when cancel button is clicked', () => {
    const onCancel = vi.fn()
    render(<DiaryForm onSubmit={vi.fn()} onCancel={onCancel} />)
    fireEvent.click(screen.getByText('取消'))
    expect(onCancel).toHaveBeenCalled()
  })

  it('should select mood when clicked', () => {
    render(<DiaryForm onSubmit={vi.fn()} />)
    const happyBtn = screen.getByText('😊').closest('button')!
    fireEvent.click(happyBtn)
    // Clicking again should deselect
    fireEvent.click(happyBtn)
  })

  it('should select occasion when clicked', () => {
    render(<DiaryForm onSubmit={vi.fn()} />)
    fireEvent.click(screen.getByText('上班'))
    // Selecting again should deselect
    fireEvent.click(screen.getByText('上班'))
  })

  it('should set rating when star is clicked', () => {
    render(<DiaryForm onSubmit={vi.fn()} />)
    const stars = screen.getAllByText('★')
    fireEvent.click(stars[2]) // Click 3rd star
  })

  it('should call onSubmit with form data when submitted', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<DiaryForm onSubmit={onSubmit} />)
    
    fireEvent.click(screen.getByText('😊').closest('button')!)
    fireEvent.click(screen.getByText('上班'))
    
    const submitBtn = screen.getByText('创建日记')
    fireEvent.click(submitBtn)
    
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
        mood: 'happy',
        occasion: '上班',
        trigger_ai_review: true,
      }))
    })
  })

  it('should use initialData when provided', () => {
    const initialData = {
      diary_date: '2026-01-10',
      mood: 'calm',
      occasion: '约会',
      notes: '测试备注',
      rating: 3,
    }
    render(<DiaryForm initialData={initialData} onSubmit={vi.fn()} />)
    expect(screen.getByText('2026年1月10日')).toBeInTheDocument()
    expect(screen.getByDisplayValue('测试备注')).toBeInTheDocument()
  })

  it('should update notes when typing', () => {
    render(<DiaryForm onSubmit={vi.fn()} />)
    const textarea = screen.getByPlaceholderText('记录今天的穿搭心得...')
    fireEvent.change(textarea, { target: { value: '新备注内容' } })
    expect(screen.getByDisplayValue('新备注内容')).toBeInTheDocument()
  })

  it('should not render cancel button when onCancel is not provided', () => {
    render(<DiaryForm onSubmit={vi.fn()} />)
    expect(screen.queryByText('取消')).not.toBeInTheDocument()
  })
})

/**
 * 今日穿搭的品类分组
 *
 * 不 mock store，直接 setState 注入衣物：分组逻辑（顺序、归「其他」、已选计数）
 * 完全依赖 groupWardrobeByCategory，走真实 store 才能保证两边口径不漂移。
 */
function makeItem(id: number, name: string, category?: string): WardrobeItem {
  return {
    id,
    user_id: 1,
    name,
    category,
    image_url: `/img/${id}.jpg`,
    primary_element: '木',
    is_custom: false,
    is_active: true,
    wear_count: 0,
    is_favorite: false,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

function groupOrder(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll('[data-outfit-group]')).map(
    (el) => el.getAttribute('data-outfit-group') as string
  )
}

describe('DiaryForm 今日穿搭品类分组', () => {
  // jsdom 不实现 Element.scrollTo。不注入的话点 chip 会在 handler 里抛错，而 React
  // 把 handler 异常收进自己的错误通道，外层 fireEvent 探不到——用 expect(...).not.toThrow()
  // 包一层就会得出假绿。改成自己记账，反而能断言到“滚到哪个元素、滚了多少”。
  let scrollCalls: { top: number; host: Element }[] = []

  beforeEach(() => {
    scrollCalls = []
    Object.defineProperty(Element.prototype, 'scrollTo', {
      configurable: true,
      writable: true,
      value(this: Element, opts: { top?: number }) {
        scrollCalls.push({ top: opts?.top ?? -1, host: this })
      },
    })
  })

  afterEach(() => {
    delete (Element.prototype as unknown as Record<string, unknown>).scrollTo
    useWardrobeStore.setState({ items: [], total: 0 })
  })

  it('按 CATEGORY_ORDER 分组渲染，并在把手上标出件数', () => {
    useWardrobeStore.setState({
      items: [makeItem(1, '跑鞋', '鞋履'), makeItem(2, '白T', '上装'), makeItem(3, '衬衫', '上装')],
      total: 3,
    })
    const { container } = render(<DiaryForm onSubmit={vi.fn()} />)
    expect(groupOrder(container)).toEqual(['上装', '鞋履'])
    expect(screen.getByText('上装')).toBeInTheDocument()
    expect(screen.getByText('2 件')).toBeInTheDocument()
    expect(screen.getByText('1 件')).toBeInTheDocument()
    // 同品类内不重复出现把手
    expect(container.querySelectorAll('[data-outfit-group="上装"]')).toHaveLength(1)
  })

  it('词表外的品类归入「其他」并排在最后', () => {
    useWardrobeStore.setState({
      items: [makeItem(1, '渔夫帽', '帽子'), makeItem(2, '白T', '上装'), makeItem(3, '牛仔裤', '下装')],
      total: 3,
    })
    const { container } = render(<DiaryForm onSubmit={vi.fn()} />)
    expect(groupOrder(container)).toEqual(['上装', '下装', '其他'])
  })

  it('只有一个品类时不出现品类快导（无处可跳）', () => {
    useWardrobeStore.setState({
      items: [makeItem(1, '白T', '上装'), makeItem(2, '衬衫', '上装')],
      total: 2,
    })
    render(<DiaryForm onSubmit={vi.fn()} />)
    expect(screen.queryByRole('button', { name: '跳转到 上装' })).not.toBeInTheDocument()
  })

  it('多品类时出现快导 chip，带上件数与已选进度', () => {
    useWardrobeStore.setState({
      items: [makeItem(1, '白T', '上装'), makeItem(2, '衬衫', '上装'), makeItem(3, '跑鞋', '鞋履')],
      total: 3,
    })
    render(<DiaryForm onSubmit={vi.fn()} />)
    const topChip = screen.getByRole('button', { name: '跳转到 上装' })
    expect(topChip).toHaveTextContent('上装2')

    // 勾一件后 chip 从「总数」变为「已选/总数」，不滚回去数也能知道选了几件
    fireEvent.click(screen.getByText('白T').closest('button')!)
    expect(topChip).toHaveTextContent(/上装\s*1\/2/)
    expect(screen.getByRole('button', { name: '跳转到 鞋履' })).toHaveTextContent('鞋履1')
  })

  it('点 chip 只滚选择区内部，并滚到目标分组的位置', () => {
    useWardrobeStore.setState({
      items: [makeItem(1, '白T', '上装'), makeItem(2, '衬衫', '上装'), makeItem(3, '跑鞋', '鞋履')],
      total: 3,
    })
    const { container } = render(<DiaryForm onSubmit={vi.fn()} />)

    const shoeGroup = container.querySelector('[data-outfit-group="鞋履"]') as HTMLElement
    expect(shoeGroup).toBeTruthy()
    // 上装分组在前，所以鞋履的 offsetTop 不是 0；拿它验证“跳对了组”
    Object.defineProperty(shoeGroup, 'offsetTop', { value: 180, configurable: true })

    fireEvent.click(screen.getByRole('button', { name: '跳转到 鞋履' }))

    expect(scrollCalls).toHaveLength(1)
    expect(scrollCalls[0].top).toBe(180)
    // 滚动发生在内滚容器上，不拖整页走
    expect(scrollCalls[0].host).not.toBe(container.ownerDocument.body)
    expect(scrollCalls[0].host.className).toContain('overflow-y-auto')
  })

  it('勾选衣物后把手与标题同步已选件数', () => {
    useWardrobeStore.setState({
      items: [makeItem(1, '白T', '上装'), makeItem(2, '衬衫', '上装'), makeItem(3, '跑鞋', '鞋履')],
      total: 3,
    })
    render(<DiaryForm onSubmit={vi.fn()} />)
    expect(screen.queryByText(/已选/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('白T').closest('button')!)
    expect(screen.getByText('已选 1')).toBeInTheDocument()
    expect(screen.getByText(/今日穿搭（已选 1 件）/)).toBeInTheDocument()

    fireEvent.click(screen.getByText('衬衫').closest('button')!)
    expect(screen.getByText('已选 2')).toBeInTheDocument()

    // 取消勾选后回到无已选态
    fireEvent.click(screen.getByText('衬衫').closest('button')!)
    expect(screen.queryByText('已选 2')).not.toBeInTheDocument()
  })

  it('选中的衣橱衣物以 wardrobe 关联项提交（导入衣橱链路）', async () => {
    useWardrobeStore.setState({
      items: [makeItem(7, '白T', '上装'), makeItem(8, '跑鞋', '鞋履')],
      total: 2,
    })
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<DiaryForm onSubmit={onSubmit} />)

    fireEvent.click(screen.getByText('白T').closest('button')!)
    fireEvent.click(screen.getByText('创建日记'))

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          items: [{ item_source: 'wardrobe', wardrobe_item_id: 7 }],
          trigger_ai_review: true,
        })
      )
    })
  })

  it('衣橱取数被 limit 截断时明说，不让人以为东西没分类', () => {
    useWardrobeStore.setState({
      items: [makeItem(1, '白T', '上装'), makeItem(2, '跑鞋', '鞋履')],
      total: 89,
    })
    render(<DiaryForm onSubmit={vi.fn()} />)
    expect(screen.getByText(/衣橱共 89 件，此处仅列出前 2 件/)).toBeInTheDocument()
  })
})
