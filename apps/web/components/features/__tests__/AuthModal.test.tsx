import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { AuthModal } from '../AuthModal'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, onClick, ...props }: any) => <div onClick={onClick} {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

// Mock lucide-react
vi.mock('lucide-react', () => ({
  X: () => <span data-testid="x-icon" />,
  Eye: () => <span data-testid="eye-icon" />,
  EyeOff: () => <span data-testid="eyeoff-icon" />,
  User: () => <span data-testid="user-icon" />,
  Lock: () => <span data-testid="lock-icon" />,
  Phone: () => <span data-testid="phone-icon" />,
  Mail: () => <span data-testid="mail-icon" />,
  ShieldCheck: () => <span data-testid="shield-icon" />,
}))

// Mock 短信验证码发送 API
const { mockSendSmsCode } = vi.hoisted(() => ({ mockSendSmsCode: vi.fn() }))
vi.mock('@/lib/api', () => ({
  sendSmsCode: mockSendSmsCode,
}))

// Configurable mock store
let mockStoreData: any = {}

vi.mock('@/store/user', () => ({
  useUserStore: () => mockStoreData,
}))

// Helper to get submit button
function getSubmitButton() {
  return document.querySelector('button[type="submit"]') as HTMLButtonElement
}

// Helper to click tab by text (tabs are type="button" buttons)
function clickTab(text: string) {
  const tabs = screen.getAllByText(text)
  // Tab buttons come before the form, so the first match is the tab
  fireEvent.click(tabs[0])
}

describe('AuthModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSendSmsCode.mockResolvedValue({ message: '验证码已发送', expires_in: 300 })
    mockStoreData = {
      login: vi.fn().mockResolvedValue(undefined),
      loginWithEmail: vi.fn().mockResolvedValue(undefined),
      register: vi.fn().mockResolvedValue(undefined),
      isLoading: false,
      error: null as string | null,
      clearError: vi.fn(),
    }
  })

  it('should return null when closed', () => {
    const { container } = render(<AuthModal isOpen={false} onClose={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('should render login title when open', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText('欢迎回来')).toBeInTheDocument()
  })

  it('should render login and register tabs', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    // "登录" appears as tab and submit button, "注册" as tab only in login mode
    expect(screen.getAllByText('登录').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('注册').length).toBeGreaterThanOrEqual(1)
  })

  it('should switch to register mode when register tab is clicked', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    clickTab('注册')
    expect(screen.getByText('创建账户')).toBeInTheDocument()
  })

  it('should switch back to login mode when login tab is clicked', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    clickTab('注册')
    clickTab('登录')
    expect(screen.getByText('欢迎回来')).toBeInTheDocument()
  })

  it('should render phone and email login type tabs', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    // "手机号" appears as tab and label
    expect(screen.getAllByText('手机号').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('邮箱').length).toBeGreaterThanOrEqual(1)
  })

  it('should show phone input by default', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByPlaceholderText('请输入手机号')).toBeInTheDocument()
  })

  it('should show email input when email tab is clicked', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    // Click the "邮箱" tab (first occurrence)
    const emailTabs = screen.getAllByText('邮箱')
    fireEvent.click(emailTabs[0])
    expect(screen.getByPlaceholderText('请输入邮箱')).toBeInTheDocument()
  })

  it('should render password input', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByPlaceholderText('请输入密码')).toBeInTheDocument()
  })

  it('should toggle password visibility', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    const passwordInput = screen.getByPlaceholderText('请输入密码')
    expect(passwordInput).toHaveAttribute('type', 'password')
    
    const toggleBtn = screen.getByTestId('eye-icon').closest('button')!
    fireEvent.click(toggleBtn)
    expect(passwordInput).toHaveAttribute('type', 'text')
    
    fireEvent.click(toggleBtn)
    expect(passwordInput).toHaveAttribute('type', 'password')
  })

  it('should render login submit button', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    expect(getSubmitButton()).toBeInTheDocument()
    expect(getSubmitButton().textContent).toBe('登录')
  })

  it('should call onClose when close button is clicked', () => {
    const onClose = vi.fn()
    render(<AuthModal isOpen={true} onClose={onClose} />)
    const closeBtn = screen.getByTestId('x-icon').closest('button')!
    fireEvent.click(closeBtn)
    expect(onClose).toHaveBeenCalled()
  })

  it('should call onClose when backdrop is clicked', () => {
    const onClose = vi.fn()
    render(<AuthModal isOpen={true} onClose={onClose} />)
    const backdrop = screen.getByText('欢迎回来').closest('.fixed')!
    fireEvent.click(backdrop)
    expect(onClose).toHaveBeenCalled()
  })

  it('should call login with phone and password', async () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    
    fireEvent.change(screen.getByPlaceholderText('请输入手机号'), { target: { value: '13800000000' } })
    fireEvent.change(screen.getByPlaceholderText('请输入密码'), { target: { value: 'password123' } })
    fireEvent.click(getSubmitButton())
    
    await waitFor(() => {
      expect(mockStoreData.login).toHaveBeenCalledWith('13800000000', 'password123')
    })
  })

  it('should call loginWithEmail when email login is used', async () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    
    const emailTabs = screen.getAllByText('邮箱')
    fireEvent.click(emailTabs[0])
    fireEvent.change(screen.getByPlaceholderText('请输入邮箱'), { target: { value: 'test@test.com' } })
    fireEvent.change(screen.getByPlaceholderText('请输入密码'), { target: { value: 'password123' } })
    fireEvent.click(getSubmitButton())
    
    await waitFor(() => {
      expect(mockStoreData.loginWithEmail).toHaveBeenCalledWith('test@test.com', 'password123')
    })
  })

  it('should show register form fields in register mode', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    clickTab('注册')
    expect(screen.getByPlaceholderText('请输入昵称（可选）')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('请输入手机号（注册必填）')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('请输入验证码')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('请输入邮箱')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('请输入密码（至少6位）')).toBeInTheDocument()
  })

  it('should render gender radio buttons in register mode', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    clickTab('注册')
    expect(screen.getByText('男')).toBeInTheDocument()
    expect(screen.getByText('女')).toBeInTheDocument()
  })

  it('should call register with form data', async () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    clickTab('注册')
    
    fireEvent.change(screen.getByPlaceholderText('请输入昵称（可选）'), { target: { value: 'TestUser' } })
    fireEvent.change(screen.getByPlaceholderText('请输入手机号（注册必填）'), { target: { value: '13800000000' } })
    fireEvent.change(screen.getByPlaceholderText('请输入验证码'), { target: { value: '123456' } })
    fireEvent.change(screen.getByPlaceholderText('请输入密码（至少6位）'), { target: { value: 'password123' } })
    // PIPL：勾选隐私政策同意后才能提交
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(getSubmitButton())
    
    await waitFor(() => {
      expect(mockStoreData.register).toHaveBeenCalledWith({
        phone: '13800000000',
        sms_code: '123456',
        email: undefined,
        password: 'password123',
        nickname: 'TestUser',
        gender: '男',
        privacy_consent: true,
      })
    })
  })

  it('should disable register submit until privacy consent is checked', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    clickTab('注册')

    fireEvent.change(screen.getByPlaceholderText('请输入手机号（注册必填）'), { target: { value: '13800000000' } })
    fireEvent.change(screen.getByPlaceholderText('请输入密码（至少6位）'), { target: { value: 'password123' } })

    // 未勾选隐私政策时提交按钮禁用
    expect(getSubmitButton()).toBeDisabled()
    fireEvent.click(screen.getByRole('checkbox'))
    expect(getSubmitButton()).not.toBeDisabled()
  })

  it('should show error when sending code with invalid phone', async () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    clickTab('注册')

    fireEvent.change(screen.getByPlaceholderText('请输入手机号（注册必填）'), { target: { value: '12345' } })
    fireEvent.click(screen.getByText('获取验证码'))

    await waitFor(() => {
      expect(screen.getByText('请先输入正确的手机号')).toBeInTheDocument()
    })
    expect(mockSendSmsCode).not.toHaveBeenCalled()
  })

  it('should call sendSmsCode and start countdown with valid phone', async () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    clickTab('注册')

    fireEvent.change(screen.getByPlaceholderText('请输入手机号（注册必填）'), { target: { value: '13800000000' } })
    fireEvent.click(screen.getByText('获取验证码'))

    await waitFor(() => {
      expect(mockSendSmsCode).toHaveBeenCalledWith('13800000000')
    })
    // 发送成功后进入 60 秒倒计时，按钮禁用
    await waitFor(() => {
      expect(screen.getByText('60s')).toBeInTheDocument()
    })
  })

  it('should show error message when error exists', () => {
    mockStoreData.error = '登录失败'
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText('登录失败')).toBeInTheDocument()
  })

  it('should show loading text when isLoading is true', () => {
    mockStoreData.isLoading = true
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText('登录中...')).toBeInTheDocument()
  })

  it('should disable submit button when loading', () => {
    mockStoreData.isLoading = true
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    expect(getSubmitButton()).toBeDisabled()
  })

  it('should call clearError when switching modes', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    clickTab('注册')
    expect(mockStoreData.clearError).toHaveBeenCalled()
  })

  it('should call onClose after successful login', async () => {
    const onClose = vi.fn()
    render(<AuthModal isOpen={true} onClose={onClose} />)
    
    fireEvent.change(screen.getByPlaceholderText('请输入手机号'), { target: { value: '13800000000' } })
    fireEvent.change(screen.getByPlaceholderText('请输入密码'), { target: { value: 'password123' } })
    fireEvent.click(getSubmitButton())
    
    await waitFor(() => {
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('should disable register button when no phone and no email', () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />)
    clickTab('注册')
    expect(getSubmitButton()).toBeDisabled()
  })
})
