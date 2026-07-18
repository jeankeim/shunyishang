import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FiveElementList } from '../FiveElementList'

describe('FiveElementList', () => {
  it('should render title', () => {
    render(<FiveElementList />)
    expect(screen.getByText('五行分析')).toBeInTheDocument()
  })

  it('should render all five elements', () => {
    render(<FiveElementList />)
    expect(screen.getByText('金')).toBeInTheDocument()
    expect(screen.getByText('木')).toBeInTheDocument()
    expect(screen.getByText('水')).toBeInTheDocument()
    expect(screen.getByText('火')).toBeInTheDocument()
    expect(screen.getByText('土')).toBeInTheDocument()
  })

  it('should render xiyongShen label when provided', () => {
    render(<FiveElementList xiyongShen={['木', '火']} />)
    expect(screen.getByText('喜用: 木、火')).toBeInTheDocument()
  })

  it('should not render xiyongShen label when empty', () => {
    render(<FiveElementList xiyongShen={[]} />)
    expect(screen.queryByText(/喜用/)).not.toBeInTheDocument()
  })

  it('should display current percentages', () => {
    const currentData = { '金': 50, '木': 30, '水': 80, '火': 20, '土': 60 }
    render(<FiveElementList currentData={currentData} xiyongShen={['金', '土']} />)
    expect(screen.getByText('50%')).toBeInTheDocument()
    expect(screen.getByText('30%')).toBeInTheDocument()
    expect(screen.getByText('80%')).toBeInTheDocument()
    expect(screen.getByText('20%')).toBeInTheDocument()
    expect(screen.getByText('60%')).toBeInTheDocument()
  })

  it('should show 缺失 tag for element with 0%', () => {
    const currentData = { '金': 0, '木': 80, '水': 20, '火': 20, '土': 20 }
    render(<FiveElementList currentData={currentData} xiyongShen={['金']} />)
    expect(screen.getByText('缺失')).toBeInTheDocument()
  })

  it('should show 充沛 tag for strong xiyong element', () => {
    const currentData = { '金': 80, '木': 20, '水': 20, '火': 20, '土': 20 }
    render(<FiveElementList currentData={currentData} xiyongShen={['金']} />)
    expect(screen.getByText('充沛')).toBeInTheDocument()
  })

  it('should show 需补充 tag for weak xiyong element', () => {
    const currentData = { '金': 20, '木': 80, '水': 20, '火': 20, '土': 20 }
    render(<FiveElementList currentData={currentData} xiyongShen={['金']} />)
    expect(screen.getByText('需补充')).toBeInTheDocument()
  })

  it('should show 偏旺 tag for strong non-xiyong element', () => {
    const currentData = { '金': 20, '木': 80, '水': 20, '火': 20, '土': 20 }
    render(<FiveElementList currentData={currentData} xiyongShen={['金']} />)
    expect(screen.getByText('偏旺')).toBeInTheDocument()
  })

  it('should show 适中 tag for weak non-xiyong non-zero element', () => {
    const currentData = { '金': 80, '木': 20, '水': 20, '火': 20, '土': 20 }
    render(<FiveElementList currentData={currentData} xiyongShen={['金']} />)
    expect(screen.getAllByText('适中').length).toBeGreaterThanOrEqual(1)
  })

  it('should render progress bars', () => {
    const currentData = { '金': 50, '木': 30, '水': 80, '火': 20, '土': 60 }
    const { container } = render(<FiveElementList currentData={currentData} />)
    const bars = container.querySelectorAll('.h-full')
    expect(bars).toHaveLength(5)
  })

  it('should show 0% when no current data', () => {
    render(<FiveElementList />)
    const zeroTexts = screen.getAllByText('0%')
    expect(zeroTexts).toHaveLength(5)
  })

  it('should show dressing advice', () => {
    const currentData = { '金': 80, '木': 20, '水': 20, '火': 20, '土': 20 }
    render(<FiveElementList currentData={currentData} xiyongShen={['木']} />)
    expect(screen.getByText(/穿搭建议/)).toBeInTheDocument()
    expect(screen.getByText(/宜多用/)).toBeInTheDocument()
  })

  it('should show balanced advice when all elements are fine', () => {
    const currentData = { '金': 60, '木': 60, '水': 20, '火': 20, '土': 60 }
    render(<FiveElementList currentData={currentData} xiyongShen={['金', '木', '土']} />)
    expect(screen.getByText(/五行均衡/)).toBeInTheDocument()
  })

  it('should not show status tags when no data', () => {
    render(<FiveElementList />)
    expect(screen.queryByText('充沛')).not.toBeInTheDocument()
    expect(screen.queryByText('需补充')).not.toBeInTheDocument()
    expect(screen.queryByText('偏旺')).not.toBeInTheDocument()
    expect(screen.queryByText('缺失')).not.toBeInTheDocument()
  })

  it('should render pillars when provided', () => {
    const pillars = { year: '甲子', month: '乙丑', day: '丙寅', hour: '丁卯' }
    render(<FiveElementList pillars={pillars} dayMaster="丙" />)
    expect(screen.getByText('我的八字')).toBeInTheDocument()
    expect(screen.getByText('甲子')).toBeInTheDocument()
    expect(screen.getByText('乙丑')).toBeInTheDocument()
    expect(screen.getByText('丙寅')).toBeInTheDocument()
    expect(screen.getByText('丁卯')).toBeInTheDocument()
    expect(screen.getByText('日元: 丙')).toBeInTheDocument()
  })

  it('should not render pillars section when no pillars', () => {
    render(<FiveElementList />)
    expect(screen.queryByText('我的八字')).not.toBeInTheDocument()
  })
})
