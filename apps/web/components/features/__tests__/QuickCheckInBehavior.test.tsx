import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// 采纳「今日穿这个」= adopt 隐性正信号的回归防线
const mocks = vi.hoisted(() => ({
  getDailyPick: vi.fn(),
  quickCheckIn: vi.fn(),
  reportBehavior: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('@/lib/api', () => mocks)

vi.mock('@/store/user', () => ({
  useUserStore: () => ({ isAuthenticated: true }),
}))

vi.mock('@/components/ui/ModalPortal', () => ({
  ModalPortal: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, onClick, ...props }: any) => <button onClick={onClick} {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

import { QuickCheckIn } from '../QuickCheckIn'

const DAILY_PICK = {
  item: { id: 5, name: '云纹真丝围巾', category: '饰品', primary_element: '金' },
  reason: '今日幸运元素为金',
  lucky_element: '金',
  lucky_color: '白',
  match_score: 88,
}

describe('QuickCheckIn 采纳埋点', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getDailyPick.mockResolvedValue(DAILY_PICK)
  })

  it('点「选这件」上报 adopt，来源固定为衣橱', async () => {
    render(<QuickCheckIn isOpen onClose={() => {}} />)

    const btn = await waitFor(() => screen.getByText('选这件'))
    fireEvent.click(btn)

    expect(mocks.reportBehavior).toHaveBeenCalledWith(undefined, 5, 'adopt', undefined, 'wardrobe')
    // 同时把单品名填入描述，保持原交互
    expect(screen.getByDisplayValue(/云纹真丝围巾/)).toBeInTheDocument()
  })

  it('采纳埋点不影响后续打卡提交', async () => {
    mocks.quickCheckIn.mockResolvedValue({
      diary_id: 12, created: true, fortune_match_score: null,
      outfit_recommendation: null, streak_days: 1, ai_tags: null,
    })
    render(<QuickCheckIn isOpen onClose={() => {}} />)

    fireEvent.click(await waitFor(() => screen.getByText('选这件')))
    fireEvent.click(screen.getByText('完成打卡 ✨'))

    await waitFor(() => expect(mocks.quickCheckIn).toHaveBeenCalled())
    expect(mocks.reportBehavior).toHaveBeenCalledTimes(1)
  })

  it('无 daily-pick 单品时点击不埋点', async () => {
    mocks.getDailyPick.mockResolvedValue({ ...DAILY_PICK, item: null })
    render(<QuickCheckIn isOpen onClose={() => {}} />)

    await waitFor(() => expect(mocks.getDailyPick).toHaveBeenCalled())
    expect(screen.queryByText('选这件')).not.toBeInTheDocument()
    expect(mocks.reportBehavior).not.toHaveBeenCalled()
  })
})
