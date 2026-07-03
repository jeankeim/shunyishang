import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DiaryCalendar } from '../DiaryCalendar'
import type { DiaryCalendarEntry } from '@/types'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, onClick, ...props }: any) => <button onClick={onClick} {...props}>{children}</button>,
  },
}))

const mockEntries: DiaryCalendarEntry[] = [
  { date: '2026-01-15', mood: 'happy', has_items: true },
  { date: '2026-01-20', mood: 'calm', has_items: false },
]

describe('DiaryCalendar', () => {
  it('should render year and month title', () => {
    render(<DiaryCalendar year={2026} month={1} entries={mockEntries} onPrevMonth={vi.fn()} onNextMonth={vi.fn()} />)
    expect(screen.getByText('2026年1月')).toBeInTheDocument()
  })

  it('should render weekday headers', () => {
    render(<DiaryCalendar year={2026} month={1} entries={mockEntries} onPrevMonth={vi.fn()} onNextMonth={vi.fn()} />)
    expect(screen.getByText('日')).toBeInTheDocument()
    expect(screen.getByText('一')).toBeInTheDocument()
    expect(screen.getByText('二')).toBeInTheDocument()
    expect(screen.getByText('三')).toBeInTheDocument()
    expect(screen.getByText('四')).toBeInTheDocument()
    expect(screen.getByText('五')).toBeInTheDocument()
    expect(screen.getByText('六')).toBeInTheDocument()
  })

  it('should render day numbers for the month', () => {
    render(<DiaryCalendar year={2026} month={1} entries={mockEntries} onPrevMonth={vi.fn()} onNextMonth={vi.fn()} />)
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('15')).toBeInTheDocument()
    expect(screen.getByText('31')).toBeInTheDocument()
  })

  it('should call onPrevMonth when prev button is clicked', () => {
    const onPrevMonth = vi.fn()
    render(<DiaryCalendar year={2026} month={1} entries={[]} onPrevMonth={onPrevMonth} onNextMonth={vi.fn()} />)
    const buttons = screen.getAllByRole('button')
    // First button is the prev month button
    fireEvent.click(buttons[0])
    expect(onPrevMonth).toHaveBeenCalled()
  })

  it('should call onNextMonth when next button is clicked', () => {
    const onNextMonth = vi.fn()
    render(<DiaryCalendar year={2026} month={1} entries={[]} onPrevMonth={vi.fn()} onNextMonth={onNextMonth} />)
    const buttons = screen.getAllByRole('button')
    // Last navigation button is the next month button (before day buttons)
    fireEvent.click(buttons[1])
    expect(onNextMonth).toHaveBeenCalled()
  })

  it('should call onDateClick when a date is clicked', () => {
    const onDateClick = vi.fn()
    render(<DiaryCalendar year={2026} month={1} entries={mockEntries} onPrevMonth={vi.fn()} onNextMonth={vi.fn()} onDateClick={onDateClick} />)
    fireEvent.click(screen.getByText('15'))
    expect(onDateClick).toHaveBeenCalledWith('2026-01-15')
  })

  it('should render mood emoji for entries with mood', () => {
    render(<DiaryCalendar year={2026} month={1} entries={mockEntries} onPrevMonth={vi.fn()} onNextMonth={vi.fn()} />)
    expect(screen.getByText('😊')).toBeInTheDocument()
    expect(screen.getByText('😌')).toBeInTheDocument()
  })

  it('should handle February with 28 days', () => {
    render(<DiaryCalendar year={2026} month={2} entries={[]} onPrevMonth={vi.fn()} onNextMonth={vi.fn()} />)
    expect(screen.getByText('28')).toBeInTheDocument()
    expect(screen.queryByText('29')).not.toBeInTheDocument()
  })

  it('should handle empty entries array', () => {
    render(<DiaryCalendar year={2026} month={1} entries={[]} onPrevMonth={vi.fn()} onNextMonth={vi.fn()} />)
    expect(screen.getByText('2026年1月')).toBeInTheDocument()
    // No emojis should be rendered
    expect(screen.queryByText('😊')).not.toBeInTheDocument()
  })
})
