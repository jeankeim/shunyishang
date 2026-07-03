import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ImageLightbox } from '../ImageLightbox'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, onClick, ...props }: any) => <div onClick={onClick} {...props}>{children}</div>,
    img: ({ src, alt, ...props }: any) => <img src={src} alt={alt} {...props} />,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

// Mock createPortal
vi.mock('react-dom', () => ({
  createPortal: (node: any) => node,
}))

describe('ImageLightbox', () => {
  it('should render image viewer', () => {
    render(<ImageLightbox imageUrl="http://example.com/img.jpg" onClose={vi.fn()} />)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('should render close button', () => {
    render(<ImageLightbox imageUrl="http://example.com/img.jpg" onClose={vi.fn()} />)
    expect(screen.getByLabelText('关闭图片查看器')).toBeInTheDocument()
  })

  it('should render loading state initially', () => {
    render(<ImageLightbox imageUrl="http://example.com/img.jpg" onClose={vi.fn()} />)
    expect(screen.getByText('正在加载高清图...')).toBeInTheDocument()
  })

  it('should call onClose when close button is clicked', () => {
    const onClose = vi.fn()
    render(<ImageLightbox imageUrl="http://example.com/img.jpg" onClose={onClose} />)
    fireEvent.click(screen.getByLabelText('关闭图片查看器'))
    expect(onClose).toHaveBeenCalled()
  })

  it('should call onClose when backdrop is clicked', () => {
    const onClose = vi.fn()
    render(<ImageLightbox imageUrl="http://example.com/img.jpg" onClose={onClose} />)
    const dialog = screen.getByRole('dialog')
    fireEvent.click(dialog)
    expect(onClose).toHaveBeenCalled()
  })

  it('should call onClose when ESC key is pressed', () => {
    const onClose = vi.fn()
    render(<ImageLightbox imageUrl="http://example.com/img.jpg" onClose={onClose} />)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })

  it('should not call onClose when other keys are pressed', () => {
    const onClose = vi.fn()
    render(<ImageLightbox imageUrl="http://example.com/img.jpg" onClose={onClose} />)
    fireEvent.keyDown(window, { key: 'Enter' })
    expect(onClose).not.toHaveBeenCalled()
  })

  it('should render image with correct src', () => {
    render(<ImageLightbox imageUrl="http://example.com/img.jpg" onClose={vi.fn()} />)
    const img = screen.getByAltText('推荐单品高清图')
    expect(img).toHaveAttribute('src', 'http://example.com/img.jpg')
  })

  it('should render aria-label', () => {
    render(<ImageLightbox imageUrl="http://example.com/img.jpg" onClose={vi.fn()} />)
    expect(screen.getByLabelText('图片查看器')).toBeInTheDocument()
  })

  it('should stop propagation when clicking on content area', () => {
    const onClose = vi.fn()
    render(<ImageLightbox imageUrl="http://example.com/img.jpg" onClose={onClose} />)
    // Click on the inner content div (not the backdrop)
    const innerDiv = screen.getByAltText('推荐单品高清图').parentElement
    if (innerDiv) {
      fireEvent.click(innerDiv)
      // onClose should not be called because stopPropagation
      expect(onClose).not.toHaveBeenCalled()
    }
  })
})
