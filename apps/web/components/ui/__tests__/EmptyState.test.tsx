import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { EmptyState } from '../EmptyState'

describe('EmptyState', () => {
  it('should render title', () => {
    render(<EmptyState title="暂无数据" />)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })

  it('should render description when provided', () => {
    render(<EmptyState title="暂无数据" description="请添加新内容" />)
    expect(screen.getByText('请添加新内容')).toBeInTheDocument()
  })

  it('should not render description when not provided', () => {
    render(<EmptyState title="暂无数据" />)
    expect(screen.queryByText('请添加新内容')).not.toBeInTheDocument()
  })

  it('should render action button when actionLabel and onAction are provided', () => {
    const onAction = vi.fn()
    render(<EmptyState title="暂无数据" actionLabel="添加" onAction={onAction} />)

    const button = screen.getByText('添加')
    expect(button).toBeInTheDocument()
  })

  it('should not render action button when only actionLabel is provided', () => {
    render(<EmptyState title="暂无数据" actionLabel="添加" />)
    expect(screen.queryByText('添加')).not.toBeInTheDocument()
  })

  it('should call onAction when button is clicked', () => {
    const onAction = vi.fn()
    render(<EmptyState title="暂无数据" actionLabel="添加" onAction={onAction} />)

    fireEvent.click(screen.getByText('添加'))
    expect(onAction).toHaveBeenCalledTimes(1)
  })

  it('should use default icon (wardrobe) when not specified', () => {
    const { container } = render(<EmptyState title="暂无数据" />)
    // The component renders an SVG icon, we just check it renders
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('should render different icons based on prop', () => {
    const { container: wardrobeContainer } = render(<EmptyState title="test" icon="wardrobe" />)
    const { container: chatContainer } = render(<EmptyState title="test" icon="chat" />)
    const { container: calendarContainer } = render(<EmptyState title="test" icon="calendar" />)
    const { container: searchContainer } = render(<EmptyState title="test" icon="search" />)
    const { container: alertContainer } = render(<EmptyState title="test" icon="alert" />)

    // All should render an SVG icon
    expect(wardrobeContainer.querySelector('svg')).toBeInTheDocument()
    expect(chatContainer.querySelector('svg')).toBeInTheDocument()
    expect(calendarContainer.querySelector('svg')).toBeInTheDocument()
    expect(searchContainer.querySelector('svg')).toBeInTheDocument()
    expect(alertContainer.querySelector('svg')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    const { container } = render(<EmptyState title="test" className="custom-class" />)
    expect(container.querySelector('.custom-class')).toBeInTheDocument()
  })
})
