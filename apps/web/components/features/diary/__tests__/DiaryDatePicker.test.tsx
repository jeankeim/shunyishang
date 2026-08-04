import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DiaryDatePicker } from '../DiaryDatePicker'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

describe('DiaryDatePicker', () => {
  it('should render trigger with formatted selected date', () => {
    render(<DiaryDatePicker value="2026-08-05" onChange={vi.fn()} maxDate="2026-08-05" />)
    expect(screen.getByText('2026年8月5日')).toBeInTheDocument()
  })

  it('should open calendar panel on trigger click', () => {
    render(<DiaryDatePicker value="2026-08-05" onChange={vi.fn()} maxDate="2026-08-05" />)
    fireEvent.click(screen.getByTestId('date-picker-trigger'))
    expect(screen.getByTestId('date-picker-panel')).toBeInTheDocument()
    expect(screen.getByText('2026年8月')).toBeInTheDocument()
  })

  it('should select a day and call onChange', () => {
    const onChange = vi.fn()
    render(<DiaryDatePicker value="2026-08-05" onChange={onChange} maxDate="2026-08-05" />)
    fireEvent.click(screen.getByTestId('date-picker-trigger'))
    // 选中 8月3日（非今天、非未来）
    fireEvent.click(screen.getByText('3'))
    expect(onChange).toHaveBeenCalledWith('2026-08-03')
  })

  it('should disable future days beyond maxDate', () => {
    render(<DiaryDatePicker value="2026-08-05" onChange={vi.fn()} maxDate="2026-08-05" />)
    fireEvent.click(screen.getByTestId('date-picker-trigger'))
    // 8月6日（未来）应被禁用
    const futureDay = screen.getByText('6').closest('button')
    expect(futureDay).toBeDisabled()
    // 8月5日（今天）可选
    const todayBtn = screen.getByText('5').closest('button')
    expect(todayBtn).not.toBeDisabled()
  })

  it('should select today via quick button', () => {
    const onChange = vi.fn()
    render(<DiaryDatePicker value="2026-08-01" onChange={onChange} maxDate="2026-08-05" />)
    fireEvent.click(screen.getByTestId('date-picker-trigger'))
    fireEvent.click(screen.getByText('选择今天'))
    expect(onChange).toHaveBeenCalledWith('2026-08-05')
  })

  it('should navigate to previous month', () => {
    render(<DiaryDatePicker value="2026-08-05" onChange={vi.fn()} maxDate="2026-08-05" />)
    fireEvent.click(screen.getByTestId('date-picker-trigger'))
    fireEvent.click(screen.getByLabelText('上一月'))
    expect(screen.getByText('2026年7月')).toBeInTheDocument()
  })
})
