import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BaziCard } from '../BaziCard'
import { useUserStore } from '@/store/user'

// Mock framer-motion to avoid animation issues in jsdom
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

const mockBazi = {
  pillars: {
    year: '甲子',
    month: '乙丑',
    day: '丙寅',
    hour: '丁卯',
  },
  eight_chars: ['甲', '子', '乙', '丑', '丙', '寅', '丁', '卯'],
  five_elements_count: { '金': 1, '木': 3, '水': 1, '火': 2, '土': 1 },
  dominant_element: '木',
  lacking_element: '金',
  day_master: '丙',
  month_element: '火',
  suggested_elements: ['木', '水'],
  avoid_elements: ['金'],
  reasoning: 'test reasoning',
}

const mockUser = {
  id: 1,
  user_code: 'U001',
  nickname: 'TestUser',
  gender: '男',
  birth_date: '1990-05-15',
  birth_time: '08:00',
  bazi: mockBazi as any,
  xiyong_elements: ['木', '水'],
}

describe('BaziCard', () => {
  beforeEach(() => {
    useUserStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    })
  })

  it('should return null when user is null', () => {
    const { container } = render(<BaziCard />)
    expect(container.firstChild).toBeNull()
  })

  it('should return null when user has no bazi', () => {
    useUserStore.setState({ user: { id: 1, user_code: 'U001' } as any })
    const { container } = render(<BaziCard />)
    expect(container.firstChild).toBeNull()
  })

  it('should render bazi card when user has bazi', () => {
    useUserStore.setState({ user: mockUser as any })
    render(<BaziCard />)
    expect(screen.getByText('我的八字')).toBeInTheDocument()
    expect(screen.getByText('已为您自动分析')).toBeInTheDocument()
  })

  it('should render four pillars', () => {
    useUserStore.setState({ user: mockUser as any })
    render(<BaziCard />)
    expect(screen.getByText('年柱')).toBeInTheDocument()
    expect(screen.getByText('月柱')).toBeInTheDocument()
    expect(screen.getByText('日柱')).toBeInTheDocument()
    expect(screen.getByText('时柱')).toBeInTheDocument()
  })

  it('should render pillar characters', () => {
    useUserStore.setState({ user: mockUser as any })
    render(<BaziCard />)
    // 甲子 for year pillar
    expect(screen.getByText('甲')).toBeInTheDocument()
    expect(screen.getByText('子')).toBeInTheDocument()
    expect(screen.getByText('乙')).toBeInTheDocument()
    expect(screen.getByText('丑')).toBeInTheDocument()
  })

  it('should render xiyong elements', () => {
    useUserStore.setState({ user: mockUser as any })
    render(<BaziCard />)
    expect(screen.getByText('喜用神')).toBeInTheDocument()
    // The suggested elements are rendered as spans
    expect(screen.getAllByText('木').length).toBeGreaterThan(0)
    expect(screen.getAllByText('水').length).toBeGreaterThan(0)
  })

  it('should render avoid elements', () => {
    useUserStore.setState({ user: mockUser as any })
    render(<BaziCard />)
    expect(screen.getByText('需避免')).toBeInTheDocument()
    expect(screen.getAllByText('金').length).toBeGreaterThan(0)
  })

  it('should render birth date and time', () => {
    useUserStore.setState({ user: mockUser as any })
    render(<BaziCard />)
    expect(screen.getByText('1990-05-15')).toBeInTheDocument()
    expect(screen.getByText('08:00')).toBeInTheDocument()
  })

  it('should call onEdit when edit button is clicked', () => {
    useUserStore.setState({ user: mockUser as any })
    const onEdit = vi.fn()
    render(<BaziCard onEdit={onEdit} />)

    fireEvent.click(screen.getByText('修改'))
    expect(onEdit).toHaveBeenCalledTimes(1)
  })

  it('should not render edit button when onEdit is not provided', () => {
    useUserStore.setState({ user: mockUser as any })
    render(<BaziCard />)
    expect(screen.queryByText('修改')).not.toBeInTheDocument()
  })

  it('should render xiyong from user.xiyong_elements when bazi.suggested_elements is undefined', () => {
    const userWithoutSuggested = {
      ...mockUser,
      bazi: { ...mockBazi, suggested_elements: undefined } as any,
    }
    useUserStore.setState({ user: userWithoutSuggested as any })
    render(<BaziCard />)
    expect(screen.getByText('喜用神')).toBeInTheDocument()
  })

  it('should not render xiyong section when no suggested elements', () => {
    const userWithoutAny = {
      ...mockUser,
      bazi: { ...mockBazi, suggested_elements: [] } as any,
      xiyong_elements: undefined,
    }
    useUserStore.setState({ user: userWithoutAny as any })
    render(<BaziCard />)
    expect(screen.queryByText('喜用神')).not.toBeInTheDocument()
  })

  it('should not render avoid section when no avoid elements', () => {
    const userWithoutAvoid = {
      ...mockUser,
      bazi: { ...mockBazi, avoid_elements: [] } as any,
    }
    useUserStore.setState({ user: userWithoutAvoid as any })
    render(<BaziCard />)
    expect(screen.queryByText('需避免')).not.toBeInTheDocument()
  })

  it('should handle bazi as string (JSON.parse)', () => {
    useUserStore.setState({
      user: { ...mockUser, bazi: JSON.stringify(mockBazi) } as any,
    })
    render(<BaziCard />)
    expect(screen.getByText('我的八字')).toBeInTheDocument()
  })

  it('should not render birth info when not available', () => {
    const userWithoutBirth = {
      ...mockUser,
      birth_date: undefined,
      birth_time: undefined,
    }
    useUserStore.setState({ user: userWithoutBirth as any })
    render(<BaziCard />)
    expect(screen.queryByText('1990-05-15')).not.toBeInTheDocument()
  })

  it('should render reasoning as qualitative description without raw scores', () => {
    const userWithScores = {
      ...mockUser,
      bazi: {
        ...mockBazi,
        reasoning: '同党(印+比劫)6.0 vs 异党(财官食伤)4.6，日元身强，喜水克、金耗（食伤泄秀为辅），忌木、火生扶。',
      } as any,
    }
    useUserStore.setState({ user: userWithScores as any })
    render(<BaziCard />)
    expect(
      screen.getByText('同党(印+比劫)势力略占优，日元身强，喜水克、金耗（食伤泄秀为辅），忌木、火生扶。')
    ).toBeInTheDocument()
    expect(screen.queryByText(/6\.0/)).not.toBeInTheDocument()
  })

  it('should describe balanced chart as 势均力敌', () => {
    const userBalanced = {
      ...mockUser,
      bazi: {
        ...mockBazi,
        reasoning: '同党5.0 vs 异党4.6，旺衰中和，参考月令规则表：春火得木生，火渐旺，喜木生、火助，忌水克、金耗',
      } as any,
    }
    useUserStore.setState({ user: userBalanced as any })
    render(<BaziCard />)
    expect(screen.getByText(/同党与异党势均力敌，旺衰中和/)).toBeInTheDocument()
  })

  it('should strip weighted scores for cong patterns', () => {
    const userCong = {
      ...mockUser,
      bazi: {
        ...mockBazi,
        reasoning: '同党(印+比劫)加权7.8/9.2独旺，财官杀仅0.4且不当令，判为从强格：顺其旺势，喜水、金，忌木、火逆势。',
      } as any,
    }
    useUserStore.setState({ user: userCong as any })
    render(<BaziCard />)
    expect(
      screen.getByText('同党(印+比劫)独旺，财官杀微弱且不当令，判为从强格：顺其旺势，喜水、金，忌木、火逆势。')
    ).toBeInTheDocument()
  })
})
