import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { SceneRescue } from '@/lib/api'
import { postSceneRescue } from '@/lib/api'
import { hasTodayDiary, logOutfitAsDiary, loggedFlagKey } from '@/lib/outfit-diary'
import { requestChatInputAutofill } from '@/lib/chatAutofill'
import { COMMON_SCENES } from '@/lib/scene-config'
import { toast } from '@/components/ui/Toast'
import { SceneRescueModal } from '../SceneRescueModal'

vi.mock('@/lib/api', () => ({
  postSceneRescue: vi.fn(),
}))
vi.mock('@/lib/image', () => ({
  getImageUrl: (url: string) => url,
}))
vi.mock('@/lib/outfit-diary', async () => {
  const actual = await vi.importActual<typeof import('@/lib/outfit-diary')>('@/lib/outfit-diary')
  return {
    ...actual,
    hasTodayDiary: vi.fn(),
    logOutfitAsDiary: vi.fn(),
  }
})
vi.mock('@/lib/chatAutofill', () => ({
  requestChatInputAutofill: vi.fn(),
}))
vi.mock('@/components/ui/Toast', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}))
vi.mock('../ItemDetailModal', () => ({
  ItemDetailModal: ({ item }: { item: { name: string } }) => (
    <div data-testid="item-detail-modal">{item.name}</div>
  ),
}))

function makeRescue(overrides: Partial<SceneRescue> = {}): SceneRescue {
  return {
    date: '2026-08-29',
    scene: '面试',
    scene_elements: { primary: ['金', '水'], secondary: ['土'] },
    scene_advice: '面试宜利落沉稳：金主决断、水主沟通，避免过于花哨的图案',
    outfit_items: [
      { id: 11, name: '藏青西装外套', category: '外套', primary_element: '金', image_url: '/img/11.png', match_score: 92, wear_count: 1, is_favorite: false },
      { id: 12, name: '白色衬衫', category: '上装', primary_element: '金', image_url: '/img/12.png', match_score: 88, wear_count: 4, is_favorite: true },
    ],
    completeness: { has_top: true, has_bottom_or_dress: true, has_shoes: false, has_accessory: false, missing: ['鞋履'] },
    reasoning: '按面试场景重排了你的衣橱',
    match_score: 90,
    weather_summary: { city: '杭州', temperature: 18, weather: '多云', element: '木' },
    fortune_summary: { lucky_elements: ['金'], lucky_colors: ['白色'], overall_score: 78 },
    style_tip: '领口保持挺括',
    ...overrides,
  }
}

describe('SceneRescueModal', () => {
  beforeEach(() => {
    vi.mocked(postSceneRescue).mockReset()
    vi.mocked(hasTodayDiary).mockReset().mockResolvedValue(false)
    vi.mocked(logOutfitAsDiary).mockReset()
    vi.mocked(requestChatInputAutofill).mockReset()
    vi.mocked(toast.info).mockReset()
    localStorage.clear()
    window.location.hash = ''
  })

  it('关闭时不渲染任何内容', () => {
    const { container } = render(<SceneRescueModal open={false} onClose={vi.fn()} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('打开后展示全部场景宫格与引导文案', async () => {
    render(<SceneRescueModal open onClose={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('场景急救搭配')).toBeInTheDocument())
    for (const scene of COMMON_SCENES) {
      expect(screen.getByText(scene.label)).toBeInTheDocument()
    }
    expect(screen.getByText('上面选一个场景，立刻从你自己的衣橱里配好一套')).toBeInTheDocument()
    expect(postSceneRescue).not.toHaveBeenCalled()
  })

  it('点场景即出方案，并带上定位城市', async () => {
    vi.mocked(postSceneRescue).mockResolvedValue(makeRescue())
    const onClose = vi.fn()
    render(<SceneRescueModal open onClose={onClose} city="北京" />)
    fireEvent.click(await screen.findByText('面试求职'))
    await waitFor(() => expect(postSceneRescue).toHaveBeenCalledWith('面试', '北京'))
    await waitFor(() =>
      expect(screen.getByText('面试宜利落沉稳：金主决断、水主沟通，避免过于花哨的图案')).toBeInTheDocument()
    )
    expect(screen.getByText('藏青西装外套')).toBeInTheDocument()
    expect(screen.getByText('90分')).toBeInTheDocument()
    expect(screen.getByText('杭州 18°C · 面试求职')).toBeInTheDocument()
  })

  it('未传城市时不传 city 参数', async () => {
    vi.mocked(postSceneRescue).mockResolvedValue(makeRescue())
    render(<SceneRescueModal open onClose={vi.fn()} />)
    fireEvent.click(await screen.findByText('面试求职'))
    await waitFor(() => expect(postSceneRescue).toHaveBeenCalledWith('面试', undefined))
  })

  it('记录场景使用频率供下次优先排序', async () => {
    vi.mocked(postSceneRescue).mockResolvedValue(makeRescue())
    render(<SceneRescueModal open onClose={vi.fn()} />)
    fireEvent.click(await screen.findByText('约会聚会'))
    await waitFor(() =>
      expect(localStorage.getItem('scene_usage_frequency')).toContain('约会')
    )
  })

  it('接口失败时展示重试并可再次请求', async () => {
    vi.mocked(postSceneRescue).mockResolvedValue(null)
    render(<SceneRescueModal open onClose={vi.fn()} />)
    fireEvent.click(await screen.findByText('商务办公'))
    await waitFor(() => expect(screen.getByText('急救方案取不到了，稍后再试')).toBeInTheDocument())
    fireEvent.click(screen.getByText('重试'))
    await waitFor(() => expect(postSceneRescue).toHaveBeenCalledTimes(2))
  })

  it('衣橱无候选时展示兜底文案与缺口占位', async () => {
    vi.mocked(postSceneRescue).mockResolvedValue(
      makeRescue({ outfit_items: [], reasoning: '衣橱里还没有能撑住这个场合的单品' })
    )
    render(<SceneRescueModal open onClose={vi.fn()} />)
    fireEvent.click(await screen.findByText('婚礼婚宴'))
    await waitFor(() =>
      expect(screen.getByText('衣橱里还没有能撑住这个场合的单品')).toBeInTheDocument()
    )
    expect(screen.queryByText('就穿这套记一笔')).not.toBeInTheDocument()
  })

  it('「就穿这套记一笔」走共享日记链路并关闭弹窗', async () => {
    vi.mocked(postSceneRescue).mockResolvedValue(makeRescue())
    vi.mocked(logOutfitAsDiary).mockResolvedValue({ ok: true })
    const onClose = vi.fn()
    render(<SceneRescueModal open onClose={onClose} />)
    fireEvent.click(await screen.findByText('面试求职'))
    fireEvent.click(await screen.findByText('就穿这套记一笔'))
    await waitFor(() =>
      expect(logOutfitAsDiary).toHaveBeenCalledWith([
        { id: 11, category: '外套' },
        { id: 12, category: '上装' },
      ])
    )
    expect(localStorage.getItem(loggedFlagKey())).toBe('1')
    expect(window.location.hash).toBe('#diary')
    expect(onClose).toHaveBeenCalled()
  })

  it('服务端已有今日日记时按钮转为已记入态且不再写库', async () => {
    vi.mocked(postSceneRescue).mockResolvedValue(makeRescue())
    vi.mocked(hasTodayDiary).mockResolvedValue(true)
    const onClose = vi.fn()
    render(<SceneRescueModal open onClose={onClose} />)
    fireEvent.click(await screen.findByText('面试求职'))
    const btn = await screen.findByText(/今日已记入 · 去日记/)
    fireEvent.click(btn)
    await waitFor(() => expect(toast.info).toHaveBeenCalled())
    expect(logOutfitAsDiary).not.toHaveBeenCalled()
    expect(window.location.hash).toBe('#diary')
    expect(onClose).toHaveBeenCalled()
  })

  it('缺口单品跳推荐并关闭弹窗', async () => {
    vi.mocked(postSceneRescue).mockResolvedValue(makeRescue())
    const onClose = vi.fn()
    render(<SceneRescueModal open onClose={onClose} />)
    fireEvent.click(await screen.findByText('面试求职'))
    fireEvent.click(await screen.findByText(/点这里补/))
    expect(requestChatInputAutofill).toHaveBeenCalledWith('推荐一件金属性的鞋履')
    expect(window.location.hash).toBe('#chat')
    expect(onClose).toHaveBeenCalled()
  })

  it('点击缩略图打开单品详情弹窗', async () => {
    vi.mocked(postSceneRescue).mockResolvedValue(makeRescue())
    render(<SceneRescueModal open onClose={vi.fn()} />)
    fireEvent.click(await screen.findByText('面试求职'))
    await waitFor(() => expect(screen.getByText('藏青西装外套')).toBeInTheDocument())
    fireEvent.click(screen.getByText('藏青西装外套'))
    await waitFor(() => expect(screen.getByTestId('item-detail-modal')).toHaveTextContent('藏青西装外套'))
  })

  it('关闭按钮触发 onClose', async () => {
    const onClose = vi.fn()
    render(<SceneRescueModal open onClose={onClose} />)
    fireEvent.click(await screen.findByLabelText('关闭'))
    expect(onClose).toHaveBeenCalled()
  })
})
