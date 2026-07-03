import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import PosterTestPage from '../page'

vi.mock('@/components/features/PosterGenerator', () => ({
  PosterGenerator: ({ isOpen, onClose }: any) =>
    isOpen ? (
      <div data-testid="poster-generator">
        <button onClick={onClose}>close</button>
      </div>
    ) : null,
}))

describe('PosterTestPage', () => {
  it('should render page title', () => {
    render(<PosterTestPage />)
    expect(screen.getByText('海报生成器测试')).toBeInTheDocument()
  })

  it('should render description', () => {
    render(<PosterTestPage />)
    expect(screen.getByText('点击按钮打开海报生成器')).toBeInTheDocument()
  })

  it('should render open button', () => {
    render(<PosterTestPage />)
    expect(screen.getByText('打开海报生成器')).toBeInTheDocument()
  })

  it('should open poster generator when button is clicked', () => {
    render(<PosterTestPage />)
    fireEvent.click(screen.getByText('打开海报生成器'))
    expect(screen.getByTestId('poster-generator')).toBeInTheDocument()
  })

  it('should close poster generator when onClose is called', () => {
    render(<PosterTestPage />)
    fireEvent.click(screen.getByText('打开海报生成器'))
    fireEvent.click(screen.getByText('close'))
    expect(screen.queryByTestId('poster-generator')).not.toBeInTheDocument()
  })
})
