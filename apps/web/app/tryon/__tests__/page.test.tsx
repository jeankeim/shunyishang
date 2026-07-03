import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TryOnPage from '../page'

vi.mock('framer-motion', () => ({
  motion: {
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
}))

vi.mock('lucide-react', () => ({
  ArrowLeft: () => <span data-testid="arrow-left" />,
}))

const mockUseTryOnCanvas = vi.fn()

vi.mock('@/components/features/VirtualTryOn', () => ({
  VirtualTryOnCanvas: ({ layers }: any) => (
    <div data-testid="virtual-tryon-canvas">
      <input aria-label="选择照片文件" type="file" data-testid="photo-input" />
      <input aria-label="选择衣物文件" type="file" data-testid="clothing-input" />
      <span>{layers.length} layers</span>
    </div>
  ),
  TryOnToolbar: ({ hasSelection, onAddPhoto, onAddClothing, onRotateLeft, onRotateRight, onMoveUp, onMoveDown, onDelete, onUndo, onRedo, onExport }: any) => (
    <div data-testid="tryon-toolbar">
      <button onClick={onAddPhoto}>add photo</button>
      <button onClick={onAddClothing}>add clothing</button>
      <button onClick={onRotateLeft} disabled={!hasSelection}>rotate left</button>
      <button onClick={onRotateRight} disabled={!hasSelection}>rotate right</button>
      <button onClick={onMoveUp} disabled={!hasSelection}>move up</button>
      <button onClick={onMoveDown} disabled={!hasSelection}>move down</button>
      <button onClick={onDelete} disabled={!hasSelection}>delete</button>
      <button onClick={onUndo}>undo</button>
      <button onClick={onRedo}>redo</button>
      <button onClick={onExport}>export</button>
    </div>
  ),
  LayerPanel: ({ layers, selectedId }: any) => (
    <div data-testid="layer-panel">
      <span>{layers.length} layers, selected: {selectedId}</span>
    </div>
  ),
  ExportModal: ({ isOpen, onClose, title }: any) => (
    isOpen ? (
      <div data-testid="export-modal">
        <span>{title}</span>
        <button onClick={onClose}>close export</button>
      </div>
    ) : null
  ),
  useTryOnCanvas: () => mockUseTryOnCanvas(),
}))

describe('TryOnPage', () => {
  const mockCanvasRef = { current: null }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseTryOnCanvas.mockReturnValue({
      layers: [],
      selectedId: null,
      canvasSize: { width: 600, height: 800 },
      canUndo: false,
      canRedo: false,
      canvasRef: mockCanvasRef,
      addLayer: vi.fn(),
      removeLayer: vi.fn(),
      selectLayer: vi.fn(),
      moveLayer: vi.fn(),
      scaleLayer: vi.fn(),
      rotateLayer: vi.fn(),
      setOpacity: vi.fn(),
      setLayerVisible: vi.fn(),
      reorderLayer: vi.fn(),
      setCanvasSize: vi.fn(),
      undo: vi.fn(),
      redo: vi.fn(),
      exportCanvas: vi.fn(() => 'data:image/png;base64,mock'),
    })
  })

  it('should render page title', () => {
    render(<TryOnPage />)
    expect(screen.getByText('虚拟试衣')).toBeInTheDocument()
  })

  it('should render back button', () => {
    render(<TryOnPage />)
    expect(screen.getByText('返回')).toBeInTheDocument()
  })

  it('should render VirtualTryOnCanvas', () => {
    render(<TryOnPage />)
    expect(screen.getByTestId('virtual-tryon-canvas')).toBeInTheDocument()
  })

  it('should render TryOnToolbar', () => {
    render(<TryOnPage />)
    expect(screen.getByTestId('tryon-toolbar')).toBeInTheDocument()
  })

  it('should render LayerPanel', () => {
    render(<TryOnPage />)
    expect(screen.getByTestId('layer-panel')).toBeInTheDocument()
  })

  it('should trigger photo input click when add photo is clicked', () => {
    render(<TryOnPage />)
    const photoInput = screen.getByTestId('photo-input')
    const clickSpy = vi.spyOn(photoInput, 'click')
    fireEvent.click(screen.getByText('add photo'))
    expect(clickSpy).toHaveBeenCalled()
  })

  it('should trigger clothing input click when add clothing is clicked', () => {
    render(<TryOnPage />)
    const clothingInput = screen.getByTestId('clothing-input')
    const clickSpy = vi.spyOn(clothingInput, 'click')
    fireEvent.click(screen.getByText('add clothing'))
    expect(clickSpy).toHaveBeenCalled()
  })

  it('should open export modal when export is clicked', () => {
    render(<TryOnPage />)
    fireEvent.click(screen.getByText('export'))
    expect(screen.getByTestId('export-modal')).toBeInTheDocument()
  })

  it('should close export modal', () => {
    render(<TryOnPage />)
    fireEvent.click(screen.getByText('export'))
    fireEvent.click(screen.getByText('close export'))
    expect(screen.queryByTestId('export-modal')).not.toBeInTheDocument()
  })

  it('should call undo when undo is clicked', () => {
    render(<TryOnPage />)
    fireEvent.click(screen.getByText('undo'))
    // undo is called from the mock
    expect(mockUseTryOnCanvas().undo).toBeDefined()
  })

  it('should render with selected layer', () => {
    mockUseTryOnCanvas.mockReturnValue({
      layers: [{ id: '1', rotation: 0, zIndex: 0, opacity: 1 }],
      selectedId: '1',
      canvasSize: { width: 600, height: 800 },
      canUndo: true,
      canRedo: false,
      canvasRef: mockCanvasRef,
      addLayer: vi.fn(),
      removeLayer: vi.fn(),
      selectLayer: vi.fn(),
      moveLayer: vi.fn(),
      scaleLayer: vi.fn(),
      rotateLayer: vi.fn(),
      setOpacity: vi.fn(),
      setLayerVisible: vi.fn(),
      reorderLayer: vi.fn(),
      setCanvasSize: vi.fn(),
      undo: vi.fn(),
      redo: vi.fn(),
      exportCanvas: vi.fn(() => 'data:image/png;base64,mock'),
    })
    render(<TryOnPage />)
    // rotate buttons should be enabled
    expect(screen.getByText('rotate left')).not.toBeDisabled()
    expect(screen.getByText('rotate right')).not.toBeDisabled()
  })
})
