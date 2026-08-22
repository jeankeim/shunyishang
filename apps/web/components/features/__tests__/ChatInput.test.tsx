import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { ChatInput } from '../ChatInput'
import { requestChatInputAutofill, consumePendingChatAutofill } from '@/lib/chatAutofill'

describe('ChatInput', () => {
  it('should render textarea and send button', () => {
    render(<ChatInput onSend={vi.fn()} />)
    expect(screen.getByPlaceholderText('描述你的穿搭需求...')).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('should update input value on change', () => {
    render(<ChatInput onSend={vi.fn()} />)
    const textarea = screen.getByPlaceholderText('描述你的穿搭需求...')
    fireEvent.change(textarea, { target: { value: '今天穿什么' } })
    expect(textarea).toHaveValue('今天穿什么')
  })

  it('should call onSend with input value when send button is clicked', () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)

    const textarea = screen.getByPlaceholderText('描述你的穿搭需求...')
    fireEvent.change(textarea, { target: { value: '面试穿搭' } })
    fireEvent.click(screen.getByRole('button'))

    expect(onSend).toHaveBeenCalledWith('面试穿搭', undefined)
  })

  it('should clear input after sending', () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)

    const textarea = screen.getByPlaceholderText('描述你的穿搭需求...')
    fireEvent.change(textarea, { target: { value: '今天穿什么' } })
    fireEvent.click(screen.getByRole('button'))

    expect(textarea).toHaveValue('')
  })

  it('should not call onSend when input is empty', () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)

    fireEvent.click(screen.getByRole('button'))
    expect(onSend).not.toHaveBeenCalled()
  })

  it('should not call onSend when input is only whitespace', () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)

    const textarea = screen.getByPlaceholderText('描述你的穿搭需求...')
    fireEvent.change(textarea, { target: { value: '   ' } })
    fireEvent.click(screen.getByRole('button'))

    expect(onSend).not.toHaveBeenCalled()
  })

  it('should call onSend when Enter key is pressed (without shift)', () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)

    const textarea = screen.getByPlaceholderText('描述你的穿搭需求...')
    fireEvent.change(textarea, { target: { value: '测试' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })

    expect(onSend).toHaveBeenCalledWith('测试', undefined)
  })

  it('should not call onSend when Enter+Shift is pressed', () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)

    const textarea = screen.getByPlaceholderText('描述你的穿搭需求...')
    fireEvent.change(textarea, { target: { value: '测试' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })

    expect(onSend).not.toHaveBeenCalled()
  })

  it('should pass bazi to onSend when provided', () => {
    const onSend = vi.fn()
    const bazi = {
      birthYear: 1990,
      birthMonth: 5,
      birthDay: 15,
      birthHour: 8,
      gender: '男' as const,
    }
    render(<ChatInput onSend={onSend} bazi={bazi} />)

    const textarea = screen.getByPlaceholderText('描述你的穿搭需求...')
    fireEvent.change(textarea, { target: { value: 'test' } })
    fireEvent.click(screen.getByRole('button'))

    expect(onSend).toHaveBeenCalledWith('test', bazi)
  })

  it('should disable textarea and button when disabled prop is true', () => {
    render(<ChatInput onSend={vi.fn()} disabled />)
    const textarea = screen.getByPlaceholderText('描述你的穿搭需求...')
    const button = screen.getByRole('button')

    expect(textarea).toBeDisabled()
    expect(button).toBeDisabled()
  })

  it('should disable send button when input is empty', () => {
    render(<ChatInput onSend={vi.fn()} />)
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
  })

  it('should enable send button when input has content', () => {
    render(<ChatInput onSend={vi.fn()} />)
    const textarea = screen.getByPlaceholderText('描述你的穿搭需求...')
    fireEvent.change(textarea, { target: { value: 'test' } })

    const button = screen.getByRole('button')
    expect(button).not.toBeDisabled()
  })
})

describe('ChatInput 场景联动自动填充', () => {
  beforeEach(() => {
    // 清理上一个用例可能遗留的 pending 联动文本
    consumePendingChatAutofill()
  })

  it('选中场景后输入框自动填充场景名称', () => {
    render(<ChatInput onSend={vi.fn()} />)
    const textarea = screen.getByPlaceholderText('描述你的穿搭需求...')
    act(() => { requestChatInputAutofill('休闲日常') })
    expect(textarea).toHaveValue('休闲日常')
  })

  it('取消场景时清空联动填充的文本', () => {
    render(<ChatInput onSend={vi.fn()} />)
    const textarea = screen.getByPlaceholderText('描述你的穿搭需求...')
    act(() => { requestChatInputAutofill('商务办公') })
    act(() => { requestChatInputAutofill('') })
    expect(textarea).toHaveValue('')
  })

  it('取消场景时保留用户已修改的内容', () => {
    render(<ChatInput onSend={vi.fn()} />)
    const textarea = screen.getByPlaceholderText('描述你的穿搭需求...')
    act(() => { requestChatInputAutofill('商务办公') })
    fireEvent.change(textarea, { target: { value: '商务办公，偏正式一点' } })
    act(() => { requestChatInputAutofill('') })
    expect(textarea).toHaveValue('商务办公，偏正式一点')
  })

  it('输入框挂载前产生的联动文本在挂载时消费', () => {
    requestChatInputAutofill('运动健身')
    render(<ChatInput onSend={vi.fn()} />)
    const textarea = screen.getByPlaceholderText('描述你的穿搭需求...')
    expect(textarea).toHaveValue('运动健身')
  })
})
