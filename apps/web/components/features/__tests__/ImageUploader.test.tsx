import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ImageUploader } from '../ImageUploader'

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Upload: () => <span data-testid="upload-icon" />,
  X: () => <span data-testid="x-icon" />,
  Image: () => <span data-testid="image-icon" />,
}))

// Mock API
const mockGetAuthToken = vi.fn()
vi.mock('@/lib/api', () => ({
  getAuthToken: () => mockGetAuthToken(),
}))

// Mock FileReader as a proper constructor
class MockFileReader {
  onload: ((e: any) => void) | null = null
  result: string = 'data:image/png;base64,mock'
  readAsDataURL = vi.fn(function(this: MockFileReader) {
    if (this.onload) {
      this.onload({ target: { result: this.result } })
    }
  })
}
vi.stubGlobal('FileReader', MockFileReader)

describe('ImageUploader', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetAuthToken.mockReturnValue(null)
  })

  it('should render upload label', () => {
    render(<ImageUploader onImageUploaded={vi.fn()} />)
    expect(screen.getByText('衣物图片')).toBeInTheDocument()
  })

  it('should render upload prompt text', () => {
    render(<ImageUploader onImageUploaded={vi.fn()} />)
    expect(screen.getByText(/点击上传/)).toBeInTheDocument()
    expect(screen.getByText(/或拖拽图片到此处/)).toBeInTheDocument()
  })

  it('should render file format hint', () => {
    render(<ImageUploader onImageUploaded={vi.fn()} />)
    expect(screen.getByText('支持 JPG、PNG 格式，最大 5MB')).toBeInTheDocument()
  })

  it('should render file input with correct accept type', () => {
    render(<ImageUploader onImageUploaded={vi.fn()} />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    expect(input).toBeInTheDocument()
    expect(input.accept).toBe('image/*')
  })

  it('should show error when uploading non-image file', () => {
    const onImageUploaded = vi.fn()
    render(<ImageUploader onImageUploaded={onImageUploaded} />)
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['test'], 'test.txt', { type: 'text/plain' })
    
    fireEvent.change(input, { target: { files: [file] } })
    
    expect(screen.getByText('请上传图片文件（JPG/PNG 等）')).toBeInTheDocument()
  })

  it('should show error when file is too large', () => {
    const onImageUploaded = vi.fn()
    render(<ImageUploader onImageUploaded={onImageUploaded} maxSize={100} />)
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['x'.repeat(200)], 'large.jpg', { type: 'image/jpeg' })
    
    fireEvent.change(input, { target: { files: [file] } })
    
    expect(screen.getByText(/图片大小不能超过/)).toBeInTheDocument()
  })

  it('should show login error when no auth token', () => {
    mockGetAuthToken.mockReturnValue(null)
    const onImageUploaded = vi.fn()
    render(<ImageUploader onImageUploaded={onImageUploaded} />)
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' })
    
    fireEvent.change(input, { target: { files: [file] } })
    
    expect(screen.getByText('请先登录后再上传图片')).toBeInTheDocument()
  })

  it('should render custom className', () => {
    render(<ImageUploader onImageUploaded={vi.fn()} className="custom-class" />)
    const container = document.querySelector('.custom-class')
    expect(container).toBeInTheDocument()
  })

  it('should trigger file input click when upload area is clicked', () => {
    render(<ImageUploader onImageUploaded={vi.fn()} />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const clickSpy = vi.spyOn(input, 'click')
    
    const uploadArea = screen.getByText('点击上传').closest('div')
    if (uploadArea) {
      fireEvent.click(uploadArea)
      expect(clickSpy).toHaveBeenCalled()
    }
  })

  it('should handle drag over event', () => {
    render(<ImageUploader onImageUploaded={vi.fn()} />)
    const dropZone = screen.getByText('点击上传').closest('div')
    if (dropZone) {
      fireEvent.dragOver(dropZone, { preventDefault: vi.fn() })
    }
  })

  it('should handle drag leave event', () => {
    render(<ImageUploader onImageUploaded={vi.fn()} />)
    const dropZone = screen.getByText('点击上传').closest('div')
    if (dropZone) {
      fireEvent.dragLeave(dropZone, { preventDefault: vi.fn() })
    }
  })

  it('should handle drop event', () => {
    render(<ImageUploader onImageUploaded={vi.fn()} />)
    const dropZone = screen.getByText('点击上传').closest('div')
    const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' })
    
    if (dropZone) {
      fireEvent.drop(dropZone, {
        preventDefault: vi.fn(),
        dataTransfer: { files: [file] },
      })
    }
    
    // Should show error (no token)
    expect(screen.getByText('请先登录后再上传图片')).toBeInTheDocument()
  })

  it('should upload successfully with valid token', async () => {
    mockGetAuthToken.mockReturnValue('valid-token')
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ image_url: 'http://example.com/uploaded.jpg' }),
    })
    vi.stubGlobal('fetch', mockFetch)
    
    const onImageUploaded = vi.fn()
    render(<ImageUploader onImageUploaded={onImageUploaded} />)
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' })
    
    fireEvent.change(input, { target: { files: [file] } })
    
    await waitFor(() => {
      expect(onImageUploaded).toHaveBeenCalledWith('http://example.com/uploaded.jpg')
    })
  })
})
