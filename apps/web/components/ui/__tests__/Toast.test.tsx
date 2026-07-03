import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ToastItem, ToastContainer, toast, Toast } from '../Toast'

describe('ToastItem', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should render success toast with message', () => {
    const toastData: Toast = {
      id: '1',
      message: '操作成功',
      type: 'success',
    }
    render(<ToastItem toast={toastData} onRemove={vi.fn()} />)
    expect(screen.getByText('操作成功')).toBeInTheDocument()
  })

  it('should render error toast with message', () => {
    const toastData: Toast = {
      id: '2',
      message: '操作失败',
      type: 'error',
    }
    render(<ToastItem toast={toastData} onRemove={vi.fn()} />)
    expect(screen.getByText('操作失败')).toBeInTheDocument()
  })

  it('should render info toast with message', () => {
    const toastData: Toast = {
      id: '3',
      message: '提示信息',
      type: 'info',
    }
    render(<ToastItem toast={toastData} onRemove={vi.fn()} />)
    expect(screen.getByText('提示信息')).toBeInTheDocument()
  })

  it('should render warning toast with message', () => {
    const toastData: Toast = {
      id: '4',
      message: '警告信息',
      type: 'warning',
    }
    render(<ToastItem toast={toastData} onRemove={vi.fn()} />)
    expect(screen.getByText('警告信息')).toBeInTheDocument()
  })

  it('should call onRemove after duration', () => {
    const onRemove = vi.fn()
    const toastData: Toast = {
      id: '5',
      message: 'Test',
      type: 'success',
      duration: 1000,
    }
    render(<ToastItem toast={toastData} onRemove={onRemove} />)

    vi.advanceTimersByTime(1000)
    expect(onRemove).toHaveBeenCalledWith('5')
  })

  it('should call onRemove with default duration (3000ms)', () => {
    const onRemove = vi.fn()
    const toastData: Toast = {
      id: '6',
      message: 'Test',
      type: 'info',
    }
    render(<ToastItem toast={toastData} onRemove={onRemove} />)

    vi.advanceTimersByTime(2999)
    expect(onRemove).not.toHaveBeenCalled()

    vi.advanceTimersByTime(1)
    expect(onRemove).toHaveBeenCalledWith('6')
  })

  it('should call onRemove when close button is clicked', () => {
    const onRemove = vi.fn()
    const toastData: Toast = {
      id: '7',
      message: 'Test',
      type: 'success',
    }
    render(<ToastItem toast={toastData} onRemove={onRemove} />)

    fireEvent.click(screen.getByLabelText('关闭通知'))
    expect(onRemove).toHaveBeenCalledWith('7')
  })
})

describe('ToastContainer', () => {
  it('should render multiple toasts', () => {
    const toasts: Toast[] = [
      { id: '1', message: 'Toast 1', type: 'success' },
      { id: '2', message: 'Toast 2', type: 'error' },
    ]
    render(<ToastContainer toasts={toasts} onRemove={vi.fn()} />)

    expect(screen.getByText('Toast 1')).toBeInTheDocument()
    expect(screen.getByText('Toast 2')).toBeInTheDocument()
  })

  it('should render empty container with no toasts', () => {
    const { container } = render(<ToastContainer toasts={[]} onRemove={vi.fn()} />)
    expect(container.querySelector('.fixed')).toBeInTheDocument()
  })
})

describe('ToastManager', () => {
  beforeEach(() => {
    // Clear all toasts by removing them
    toast['toasts'].forEach((t) => toast.remove(t.id))
  })

  it('should add a toast and return id', () => {
    const id = toast.add('Test message', 'info')
    expect(id).toBeDefined()
    expect(typeof id).toBe('string')
  })

  it('should notify subscribers when toast is added', () => {
    const listener = vi.fn()
    const unsubscribe = toast.subscribe(listener)

    toast.add('Test', 'success')

    expect(listener).toHaveBeenCalled()
    const notifiedToasts = listener.mock.calls[0][0]
    expect(notifiedToasts).toHaveLength(1)
    expect(notifiedToasts[0].message).toBe('Test')

    unsubscribe()
  })

  it('should remove a toast', () => {
    const listener = vi.fn()
    toast.subscribe(listener)

    const id = toast.add('Test')
    listener.mockClear()

    toast.remove(id)

    expect(listener).toHaveBeenCalled()
    const notifiedToasts = listener.mock.calls[0][0]
    expect(notifiedToasts).toHaveLength(0)
  })

  it('should unsubscribe listener', () => {
    const listener = vi.fn()
    const unsubscribe = toast.subscribe(listener)

    unsubscribe()

    toast.add('Test')
    expect(listener).not.toHaveBeenCalled()
  })

  it('should add success toast via success()', () => {
    const listener = vi.fn()
    toast.subscribe(listener)

    toast.success('Success message')

    const notifiedToasts = listener.mock.calls[0][0]
    expect(notifiedToasts[0].type).toBe('success')
    expect(notifiedToasts[0].message).toBe('Success message')
  })

  it('should add error toast via error()', () => {
    const listener = vi.fn()
    toast.subscribe(listener)

    toast.error('Error message')

    const notifiedToasts = listener.mock.calls[0][0]
    expect(notifiedToasts[0].type).toBe('error')
  })

  it('should add info toast via info()', () => {
    const listener = vi.fn()
    toast.subscribe(listener)

    toast.info('Info message')

    const notifiedToasts = listener.mock.calls[0][0]
    expect(notifiedToasts[0].type).toBe('info')
  })

  it('should add warning toast via warning()', () => {
    const listener = vi.fn()
    toast.subscribe(listener)

    toast.warning('Warning message')

    const notifiedToasts = listener.mock.calls[0][0]
    expect(notifiedToasts[0].type).toBe('warning')
  })

  it('should pass duration to toast', () => {
    const listener = vi.fn()
    toast.subscribe(listener)

    toast.success('Test', 5000)

    const notifiedToasts = listener.mock.calls[0][0]
    expect(notifiedToasts[0].duration).toBe(5000)
  })
})
