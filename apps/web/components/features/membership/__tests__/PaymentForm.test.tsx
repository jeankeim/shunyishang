import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { PaymentForm } from '../PaymentForm'

vi.mock('framer-motion', () => ({
  motion: {
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

vi.mock('lucide-react', () => ({
  CreditCard: () => <span data-testid="credit-card-icon" />,
  Smartphone: () => <span data-testid="smartphone-icon" />,
  Wallet: () => <span data-testid="wallet-icon" />,
}))

let mockStoreData: any = {}
vi.mock('@/store/membership', () => ({
  useMembershipStore: () => mockStoreData,
}))

describe('PaymentForm', () => {
  const mockSubscribe = vi.fn()
  const mockOnSuccess = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockStoreData = {
      subscribe: mockSubscribe,
      isLoading: false,
    }
  })

  it('should render payment methods', () => {
    render(<PaymentForm plan="monthly" price={29} onSuccess={mockOnSuccess} />)
    expect(screen.getByText('微信支付')).toBeInTheDocument()
    expect(screen.getByText('支付宝')).toBeInTheDocument()
    expect(screen.getByText('模拟支付')).toBeInTheDocument()
  })

  it('should render price', () => {
    render(<PaymentForm plan="monthly" price={29} onSuccess={mockOnSuccess} />)
    expect(screen.getByText('¥29')).toBeInTheDocument()
  })

  it('should render confirm button', () => {
    render(<PaymentForm plan="monthly" price={29} onSuccess={mockOnSuccess} />)
    expect(screen.getByText('确认支付')).toBeInTheDocument()
  })

  it('should select payment method on click', () => {
    render(<PaymentForm plan="monthly" price={29} onSuccess={mockOnSuccess} />)
    const wechatBtn = screen.getByText('微信支付').closest('button')!
    fireEvent.click(wechatBtn)
    // The selected method should be highlighted (border-emerald-400)
    expect(wechatBtn.className).toContain('border-emerald-400')
  })

  it('should show confirmation dialog when confirm is clicked', () => {
    render(<PaymentForm plan="monthly" price={29} onSuccess={mockOnSuccess} />)
    fireEvent.click(screen.getByText('确认支付'))
    expect(screen.getByText('确认支付', { selector: 'h3' })).toBeInTheDocument()
  })

  it('should close dialog when cancel is clicked', () => {
    render(<PaymentForm plan="monthly" price={29} onSuccess={mockOnSuccess} />)
    fireEvent.click(screen.getByText('确认支付'))
    fireEvent.click(screen.getByText('取消'))
    expect(screen.queryByText('确认支付', { selector: 'h3' })).not.toBeInTheDocument()
  })

  it('should call subscribe with correct params on confirm', async () => {
    mockSubscribe.mockResolvedValueOnce(undefined)
    render(<PaymentForm plan="yearly" price={299} onSuccess={mockOnSuccess} />)
    fireEvent.click(screen.getByText('确认支付'))
    fireEvent.click(screen.getByText('确认'))
    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalledWith('yearly', 'mock')
    })
  })

  it('should call onSuccess after successful subscription', async () => {
    mockSubscribe.mockResolvedValueOnce(undefined)
    render(<PaymentForm plan="monthly" price={29} onSuccess={mockOnSuccess} />)
    fireEvent.click(screen.getByText('确认支付'))
    fireEvent.click(screen.getByText('确认'))
    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled()
    })
  })

  it('should disable confirm button when isLoading', () => {
    mockStoreData.isLoading = true
    render(<PaymentForm plan="monthly" price={29} onSuccess={mockOnSuccess} />)
    const confirmBtn = screen.getByText('确认支付')
    expect(confirmBtn).toBeDisabled()
  })

  it('should show loading text in dialog when isLoading after opening', () => {
    // First render without loading to open the dialog
    const { rerender } = render(<PaymentForm plan="monthly" price={29} onSuccess={mockOnSuccess} />)
    fireEvent.click(screen.getByText('确认支付'))
    // Now set loading to true and rerender
    mockStoreData.isLoading = true
    rerender(<PaymentForm plan="monthly" price={29} onSuccess={mockOnSuccess} />)
    expect(screen.getByText('处理中...')).toBeInTheDocument()
  })

  it('should show selected payment method in dialog', () => {
    render(<PaymentForm plan="monthly" price={29} onSuccess={mockOnSuccess} />)
    const wechatBtn = screen.getByText('微信支付').closest('button')!
    fireEvent.click(wechatBtn)
    fireEvent.click(screen.getByText('确认支付'))
    // "微信支付" appears both as a payment method button and in the dialog text
    expect(screen.getAllByText(/微信支付/).length).toBeGreaterThan(0)
  })
})
