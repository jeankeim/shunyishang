import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { DiaryForm } from '../DiaryForm'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, onClick, type, disabled, ...props }: any) => (
      <button onClick={onClick} type={type} disabled={disabled} {...props}>{children}</button>
    ),
  },
}))

describe('DiaryForm', () => {
  it('should render date input with today as default', () => {
    render(<DiaryForm onSubmit={vi.fn()} />)
    const today = new Date().toISOString().split('T')[0]
    const dateInput = screen.getByDisplayValue(today)
    expect(dateInput).toBeInTheDocument()
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
    expect(screen.getByDisplayValue('2026-01-10')).toBeInTheDocument()
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
