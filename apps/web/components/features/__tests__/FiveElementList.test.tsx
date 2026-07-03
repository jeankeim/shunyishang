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
    expect(screen.getByText('喜用: 木, 火')).toBeInTheDocument()
  })

  it('should not render xiyongShen label when empty', () => {
    render(<FiveElementList xiyongShen={[]} />)
    expect(screen.queryByText(/喜用/)).not.toBeInTheDocument()
  })

  it('should not render xiyongShen label when undefined', () => {
    render(<FiveElementList />)
    expect(screen.queryByText(/喜用/)).not.toBeInTheDocument()
  })

  it('should display current percentages', () => {
    const currentData = {
      metal: 0.5,
      wood: 0.3,
      water: 0.8,
      fire: 0.2,
      earth: 0.6,
    }
    render(<FiveElementList currentData={currentData} />)
    expect(screen.getByText('现 50%')).toBeInTheDocument()
    expect(screen.getByText('现 30%')).toBeInTheDocument()
    expect(screen.getByText('现 80%')).toBeInTheDocument()
    expect(screen.getByText('现 20%')).toBeInTheDocument()
    expect(screen.getByText('现 60%')).toBeInTheDocument()
  })

  it('should display suggested percentages when > 0', () => {
    const suggestedData = {
      metal: 0.4,
      wood: 0.6,
      water: 0,
      fire: 0,
      earth: 0,
    }
    render(<FiveElementList suggestedData={suggestedData} />)
    expect(screen.getByText('→ 40%')).toBeInTheDocument()
    expect(screen.getByText('→ 60%')).toBeInTheDocument()
  })

  it('should not display suggested percentage when 0', () => {
    const suggestedData = {
      metal: 0,
      wood: 0,
      water: 0,
      fire: 0,
      earth: 0,
    }
    render(<FiveElementList suggestedData={suggestedData} />)
    expect(screen.queryByText(/→/)).not.toBeInTheDocument()
  })

  it('should render progress bars', () => {
    const currentData = {
      metal: 0.5,
      wood: 0.3,
      water: 0.8,
      fire: 0.2,
      earth: 0.6,
    }
    const { container } = render(<FiveElementList currentData={currentData} />)
    const bars = container.querySelectorAll('.h-full')
    expect(bars).toHaveLength(5)
  })

  it('should show 0% when no current data', () => {
    render(<FiveElementList />)
    const zeroTexts = screen.getAllByText('现 0%')
    expect(zeroTexts).toHaveLength(5)
  })
})
