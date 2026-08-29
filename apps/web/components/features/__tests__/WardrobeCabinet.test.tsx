import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import type { WardrobeItem } from '@/lib/api'
import { WardrobeCabinet } from '../WardrobeCabinet'
import { WardrobeItemViewer } from '../WardrobeItemViewer'

// 灯箱/放大层用 createPortal 渲染到 body，测试里直接渲染到容器即可
vi.mock('react-dom', async () => {
  const actual = await vi.importActual<typeof import('react-dom')>('react-dom')
  return { ...actual, createPortal: (node: React.ReactNode) => node }
})

function makeItem(id: number, overrides: Partial<WardrobeItem> = {}): WardrobeItem {
  return {
    id,
    user_id: 1,
    name: `米白羊毛大衣 ${id}`,
    category: '外套',
    primary_element: '土',
    is_custom: false,
    is_active: true,
    wear_count: 2,
    is_favorite: false,
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
    ...overrides,
  }
}

describe('WardrobeCabinet', () => {
  const items = [
    makeItem(1),
    makeItem(2, { category: '上装' }),
    makeItem(3, { category: '上装' }),
    makeItem(4, { category: '鞋履' }),
  ]

  it('一格一个品类，把手上刻品类名与实时件数', () => {
    render(<WardrobeCabinet items={items} onSelect={vi.fn()} />)
    expect(screen.getByRole('button', { name: /上装/ })).toBeInTheDocument()
    expect(screen.getByText('2 件')).toBeInTheDocument()
    // 外套与鞋履各 1 件
    expect(screen.getAllByText('1 件')).toHaveLength(2)
    // 柜顶汇总
    expect(screen.getByText('共 4 件')).toBeInTheDocument()
  })

  it('只展开一格，点击其他抽屉会切换', () => {
    render(<WardrobeCabinet items={items} onSelect={vi.fn()} />)
    const topDrawer = screen.getByRole('button', { name: /上装/ })
    const shoeDrawer = screen.getByRole('button', { name: /鞋履/ })
    expect(topDrawer).toHaveAttribute('aria-expanded', 'true')
    expect(shoeDrawer).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(shoeDrawer)
    expect(shoeDrawer).toHaveAttribute('aria-expanded', 'true')
    expect(topDrawer).toHaveAttribute('aria-expanded', 'false')
  })

  it('点击抽屉内衣物触发放大查看', () => {
    const onSelect = vi.fn()
    render(<WardrobeCabinet items={items} onSelect={onSelect} />)
    fireEvent.click(screen.getAllByLabelText(/^放大查看/)[0])
    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect.mock.calls[0][0].category).toBe('上装')
  })

  it('筛选态下徽标显示「命中 / 全量」', () => {
    render(
      <WardrobeCabinet
        items={items}
        filtered
        categoryAvail={{ 上装: 9, 外套: 5, 鞋履: 3 }}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('2 / 9')).toBeInTheDocument()
    expect(screen.getByText('1 / 5')).toBeInTheDocument()
  })

  it('件数与全量一致时只显示单一数字，不啰嗦', () => {
    render(
      <WardrobeCabinet
        items={[makeItem(2, { category: '上装' }), makeItem(3, { category: '上装' })]}
        filtered
        categoryAvail={{ 上装: 2 }}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('2 件')).toBeInTheDocument()
  })

  it('品类缺失的衣物归入「其他」抽屉，不会丢件', () => {
    render(<WardrobeCabinet items={[makeItem(1, { category: undefined })]} onSelect={vi.fn()} />)
    expect(screen.getByRole('button', { name: /其他/ })).toBeInTheDocument()
    expect(screen.getByText('共 1 件')).toBeInTheDocument()
  })
})

describe('WardrobeItemViewer', () => {
  const item = makeItem(1, { secondary_element: '木', color: '米白', material: '羊毛', idle_days: 120 })

  it('渲染放大层并展示名称、品类与五行', () => {
    render(<WardrobeItemViewer item={item} onClose={vi.fn()} />)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('米白羊毛大衣 1')).toBeInTheDocument()
    expect(screen.getByText('外套 · 次五行 木')).toBeInTheDocument()
    expect(screen.getByText('羊毛')).toBeInTheDocument()
  })

  it('闲置较久的衣物带闲置徽标', () => {
    render(<WardrobeItemViewer item={item} onClose={vi.fn()} />)
    expect(screen.getByText('已闲置 120 天')).toBeInTheDocument()
  })

  it('item 为 null 时不渲染任何内容', () => {
    render(<WardrobeItemViewer item={null} onClose={vi.fn()} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('关闭按钮与遮罩点击都触发 onClose', () => {
    const onClose = vi.fn()
    render(<WardrobeItemViewer item={item} onClose={onClose} />)
    fireEvent.click(screen.getByLabelText('关闭放大查看'))
    fireEvent.click(screen.getByRole('dialog'))
    expect(onClose).toHaveBeenCalledTimes(2)
  })

  it('放大层内可直接编辑/删除，且不会误触发关闭', () => {
    const onClose = vi.fn()
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    render(<WardrobeItemViewer item={item} onClose={onClose} onEdit={onEdit} onDelete={onDelete} />)
    fireEvent.click(screen.getByRole('button', { name: '编辑衣物' }))
    fireEvent.click(screen.getByRole('button', { name: '删除衣物' }))
    expect(onEdit).toHaveBeenCalledWith(item)
    expect(onDelete).toHaveBeenCalledWith(1)
    expect(onClose).not.toHaveBeenCalled()
  })
})
