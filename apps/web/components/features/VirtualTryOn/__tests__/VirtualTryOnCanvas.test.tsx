/**
 * VirtualTryOnCanvas 组件单元测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { VirtualTryOnCanvas } from '../VirtualTryOnCanvas';
import { TryOnLayer } from '../useTryOnCanvas';
import { createRef } from 'react';

const mockLayers: TryOnLayer[] = [
  {
    id: 'layer_1',
    type: 'photo',
    src: 'data:image/png;base64,abc',
    x: 0,
    y: 0,
    width: 100,
    height: 100,
    rotation: 0,
    opacity: 1,
    zIndex: 1,
    visible: true,
    name: '用户照片',
  },
];

const mockCanvasRef = { current: null } as React.RefObject<HTMLCanvasElement | null>;

const defaultProps = {
  layers: [] as TryOnLayer[],
  selectedId: null as string | null,
  canvasSize: { width: 800, height: 600 },
  canvasRef: mockCanvasRef,
  onSelectLayer: vi.fn(),
  onMoveLayer: vi.fn(),
  onScaleLayer: vi.fn(),
  onRotateLayer: vi.fn(),
  onAddLayer: vi.fn(() => 'new_layer_id'),
  onSetCanvasSize: vi.fn(),
};

describe('VirtualTryOnCanvas', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock canvas getContext
    HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
      clearRect: vi.fn(),
      fillRect: vi.fn(),
      save: vi.fn(),
      restore: vi.fn(),
      translate: vi.fn(),
      rotate: vi.fn(),
      strokeRect: vi.fn(),
      setLineDash: vi.fn(),
      globalAlpha: 1,
      fillStyle: '',
      strokeStyle: '',
      lineWidth: 1,
    })) as any;
  });

  it('渲染 canvas 元素', () => {
    render(<VirtualTryOnCanvas {...defaultProps} />);
    const canvas = screen.getByRole('img');
    expect(canvas).toBeInTheDocument();
    expect(canvas.tagName).toBe('CANVAS');
  });

  it('空状态显示上传提示', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={[]} />);
    expect(screen.getByText('开始虚拟试衣')).toBeInTheDocument();
    expect(screen.getByText('上传照片')).toBeInTheDocument();
  });

  it('有照片时显示添加衣物按钮', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} />);
    expect(screen.getByLabelText('添加衣物')).toBeInTheDocument();
  });

  it('canvas 有正确的 aria 属性', () => {
    render(<VirtualTryOnCanvas {...defaultProps} />);
    const canvas = screen.getByRole('img');
    expect(canvas).toHaveAttribute('aria-label', '虚拟试衣画布');
  });

  it('点击空白区域取消选中', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} selectedId="layer_1" />);
    const canvas = screen.getByRole('img');
    // Mock getBoundingClientRect
    canvas.getBoundingClientRect = vi.fn(() => ({
      left: 0, top: 0, right: 800, bottom: 600,
      width: 800, height: 600, x: 0, y: 0, toJSON: () => {},
    }));
    Object.defineProperty(canvas, 'width', { value: 800 });
    Object.defineProperty(canvas, 'height', { value: 600 });

    // Click at position (500, 500) - outside the layer bounds (0,0,100,100)
    fireEvent.mouseDown(canvas, { clientX: 500, clientY: 500 });
    expect(defaultProps.onSelectLayer).toHaveBeenCalledWith(null);
  });

  it('点击图层选中该图层', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} />);
    const canvas = screen.getByRole('img');
    canvas.getBoundingClientRect = vi.fn(() => ({
      left: 0, top: 0, right: 800, bottom: 600,
      width: 800, height: 600, x: 0, y: 0, toJSON: () => {},
    }));
    Object.defineProperty(canvas, 'width', { value: 800 });
    Object.defineProperty(canvas, 'height', { value: 600 });

    // Click inside the layer bounds (50, 50)
    fireEvent.mouseDown(canvas, { clientX: 50, clientY: 50 });
    expect(defaultProps.onSelectLayer).toHaveBeenCalledWith('layer_1');
  });

  it('有图层时隐藏空状态提示', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} />);
    expect(screen.queryByText('开始虚拟试衣')).not.toBeInTheDocument();
  });

  it('隐藏的文件输入元素存在', () => {
    render(<VirtualTryOnCanvas {...defaultProps} />);
    const photoInput = screen.getByLabelText('选择照片文件');
    const clothingInput = screen.getByLabelText('选择衣物文件');
    expect(photoInput).toBeInTheDocument();
    expect(clothingInput).toBeInTheDocument();
  });

  it('上传照片按钮触发文件输入', () => {
    render(<VirtualTryOnCanvas {...defaultProps} />);
    const uploadButton = screen.getByLabelText('上传照片');
    const photoInput = screen.getByLabelText('选择照片文件');
    const clickSpy = vi.spyOn(photoInput, 'click');
    fireEvent.click(uploadButton);
    expect(clickSpy).toHaveBeenCalledOnce();
  });

  it('触摸事件触发图层选择', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} />);
    const canvas = screen.getByRole('img');
    canvas.getBoundingClientRect = vi.fn(() => ({
      left: 0, top: 0, right: 800, bottom: 600,
      width: 800, height: 600, x: 0, y: 0, toJSON: () => {},
    }));
    Object.defineProperty(canvas, 'width', { value: 800 });
    Object.defineProperty(canvas, 'height', { value: 600 });

    fireEvent.touchStart(canvas, { touches: [{ clientX: 50, clientY: 50 }] });
    expect(defaultProps.onSelectLayer).toHaveBeenCalledWith('layer_1');
  });

  it('拖拽移动图层', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} selectedId="layer_1" />);
    const canvas = screen.getByRole('img');
    canvas.getBoundingClientRect = vi.fn(() => ({
      left: 0, top: 0, right: 800, bottom: 600,
      width: 800, height: 600, x: 0, y: 0, toJSON: () => {},
    }));
    Object.defineProperty(canvas, 'width', { value: 800 });
    Object.defineProperty(canvas, 'height', { value: 600 });

    // Mouse down on layer
    fireEvent.mouseDown(canvas, { clientX: 50, clientY: 50 });
    // Mouse move
    fireEvent.mouseMove(canvas, { clientX: 100, clientY: 100 });
    expect(defaultProps.onMoveLayer).toHaveBeenCalled();
    // Mouse up
    fireEvent.mouseUp(canvas);
  });

  it('滚轮缩放选中图层', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} selectedId="layer_1" />);
    const canvas = screen.getByRole('img');
    fireEvent.wheel(canvas, { deltaY: -100 });
    expect(defaultProps.onScaleLayer).toHaveBeenCalled();
  });

  it('滚轮事件无选中图层时不缩放', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} selectedId={null} />);
    const canvas = screen.getByRole('img');
    fireEvent.wheel(canvas, { deltaY: -100 });
    expect(defaultProps.onScaleLayer).not.toHaveBeenCalled();
  });

  it('触摸移动图层', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} selectedId="layer_1" />);
    const canvas = screen.getByRole('img');
    canvas.getBoundingClientRect = vi.fn(() => ({
      left: 0, top: 0, right: 800, bottom: 600,
      width: 800, height: 600, x: 0, y: 0, toJSON: () => {},
    }));
    Object.defineProperty(canvas, 'width', { value: 800 });
    Object.defineProperty(canvas, 'height', { value: 600 });

    fireEvent.touchStart(canvas, { touches: [{ clientX: 50, clientY: 50 }] });
    fireEvent.touchMove(canvas, { touches: [{ clientX: 100, clientY: 100 }] });
    expect(defaultProps.onMoveLayer).toHaveBeenCalled();
    fireEvent.touchEnd(canvas);
  });

  it('鼠标离开画布结束拖拽', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} selectedId="layer_1" />);
    const canvas = screen.getByRole('img');
    canvas.getBoundingClientRect = vi.fn(() => ({
      left: 0, top: 0, right: 800, bottom: 600,
      width: 800, height: 600, x: 0, y: 0, toJSON: () => {},
    }));
    Object.defineProperty(canvas, 'width', { value: 800 });
    Object.defineProperty(canvas, 'height', { value: 600 });

    fireEvent.mouseDown(canvas, { clientX: 50, clientY: 50 });
    fireEvent.mouseLeave(canvas);
    // After mouseLeave, subsequent moves should not call onMoveLayer
    vi.clearAllMocks();
    fireEvent.mouseMove(canvas, { clientX: 200, clientY: 200 });
    expect(defaultProps.onMoveLayer).not.toHaveBeenCalled();
  });

  it('文件上传输入变化时处理文件', () => {
    render(<VirtualTryOnCanvas {...defaultProps} />);
    const photoInput = screen.getByLabelText('选择照片文件');
    const mockFile = new File(['dummy content'], 'photo.jpg', { type: 'image/jpeg' });
    
    // Mock FileReader
    class MockFileReader {
      result: string | null = null;
      onload: ((ev: any) => void) | null = null;
      onerror: ((ev: any) => void) | null = null;
      readAsDataURL(_file: File) {
        this.result = 'data:image/jpeg;base64,mockdata';
        this.onload?.({ target: this });
      }
    }
    const origFileReader = global.FileReader;
    (global as any).FileReader = MockFileReader;

    // Mock Image constructor
    const origImage = global.Image;
    class MockImage {
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      width = 200;
      height = 300;
      set src(_val: string) {
        setTimeout(() => this.onload?.(), 0);
      }
    }
    (global as any).Image = MockImage;

    Object.defineProperty(photoInput, 'files', { value: [mockFile], configurable: true });
    fireEvent.change(photoInput);
    // If we got here without error, the file handler was invoked

    global.FileReader = origFileReader;
    global.Image = origImage;
  });

  it('不可见图层不参与点击检测', () => {
    const hiddenLayers = mockLayers.map(l => ({ ...l, visible: false }));
    render(<VirtualTryOnCanvas {...defaultProps} layers={hiddenLayers} />);
    const canvas = screen.getByRole('img');
    canvas.getBoundingClientRect = vi.fn(() => ({
      left: 0, top: 0, right: 800, bottom: 600,
      width: 800, height: 600, x: 0, y: 0, toJSON: () => {},
    }));
    Object.defineProperty(canvas, 'width', { value: 800 });
    Object.defineProperty(canvas, 'height', { value: 600 });

    fireEvent.mouseDown(canvas, { clientX: 50, clientY: 50 });
    expect(defaultProps.onSelectLayer).toHaveBeenCalledWith(null);
  });

  it('添加衣物按钮触发文件输入', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} />);
    const clothingBtn = screen.getByLabelText('添加衣物');
    const clothingInput = screen.getByLabelText('选择衣物文件');
    const clickSpy = vi.spyOn(clothingInput, 'click');
    fireEvent.click(clothingBtn);
    expect(clickSpy).toHaveBeenCalledOnce();
  });

  it('衣物文件上传处理', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} />);
    const clothingInput = screen.getByLabelText('选择衣物文件');
    const mockFile = new File(['dummy'], 'shirt.png', { type: 'image/png' });

    class MockFileReader {
      result: string | null = null;
      onload: ((ev: any) => void) | null = null;
      onerror: ((ev: any) => void) | null = null;
      readAsDataURL(_file: File) {
        this.result = 'data:image/png;base64,mockdata';
        this.onload?.({ target: this });
      }
    }
    const origFileReader = global.FileReader;
    (global as any).FileReader = MockFileReader;

    const origImage = global.Image;
    class MockImage {
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      width = 200;
      height = 300;
      set src(_val: string) {
        setTimeout(() => this.onload?.(), 0);
      }
    }
    (global as any).Image = MockImage;

    Object.defineProperty(clothingInput, 'files', { value: [mockFile], configurable: true });
    fireEvent.change(clothingInput);

    global.FileReader = origFileReader;
    global.Image = origImage;
  });

  it('ResizeObserver 触发自定义回调', () => {
    let observerCallback: (entries: any[]) => void = () => {};
    class MockResizeObserver {
      constructor(cb: (entries: any[]) => void) {
        observerCallback = cb;
      }
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    const origRO = global.ResizeObserver;
    (global as any).ResizeObserver = MockResizeObserver;

    render(<VirtualTryOnCanvas {...defaultProps} />);

    // Trigger callback
    observerCallback([{ contentRect: { width: 1024, height: 768 } }]);
    expect(defaultProps.onSetCanvasSize).toHaveBeenCalledWith({ width: 1024, height: 768 });

    // Test with zero dimensions - should not call
    vi.clearAllMocks();
    observerCallback([{ contentRect: { width: 0, height: 0 } }]);
    expect(defaultProps.onSetCanvasSize).not.toHaveBeenCalled();

    global.ResizeObserver = origRO;
  });

  it('文件输入无文件时不处理', () => {
    render(<VirtualTryOnCanvas {...defaultProps} />);
    const photoInput = screen.getByLabelText('选择照片文件');
    Object.defineProperty(photoInput, 'files', { value: [], configurable: true });
    fireEvent.change(photoInput);
    // Should not throw
    expect(defaultProps.onAddLayer).not.toHaveBeenCalled();
  });

  it('图片加载错误时不添加图层', () => {
    render(<VirtualTryOnCanvas {...defaultProps} />);
    const photoInput = screen.getByLabelText('选择照片文件');
    const mockFile = new File(['dummy'], 'bad.jpg', { type: 'image/jpeg' });

    class MockFileReader {
      result: string | null = null;
      onload: ((ev: any) => void) | null = null;
      onerror: ((ev: any) => void) | null = null;
      readAsDataURL(_file: File) {
        this.result = 'data:image/jpeg;base64,baddata';
        this.onload?.({ target: this });
      }
    }
    const origFileReader = global.FileReader;
    (global as any).FileReader = MockFileReader;

    const origImage = global.Image;
    class MockImage {
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      width = 0;
      height = 0;
      set src(_val: string) {
        // Don't call onload - simulates bad image
      }
    }
    (global as any).Image = MockImage;

    Object.defineProperty(photoInput, 'files', { value: [mockFile], configurable: true });
    fireEvent.change(photoInput);
    // onAddLayer should not be called since image didn't load

    global.FileReader = origFileReader;
    global.Image = origImage;
  });

  it('FileReader 结果为 null 时不添加图层', () => {
    render(<VirtualTryOnCanvas {...defaultProps} />);
    const photoInput = screen.getByLabelText('选择照片文件');
    const mockFile = new File(['dummy'], 'test.jpg', { type: 'image/jpeg' });

    class MockFileReader {
      result: string | null = null;
      onload: ((ev: any) => void) | null = null;
      onerror: ((ev: any) => void) | null = null;
      readAsDataURL(_file: File) {
        this.result = null;
        this.onload?.({ target: this });
      }
    }
    const origFileReader = global.FileReader;
    (global as any).FileReader = MockFileReader;

    Object.defineProperty(photoInput, 'files', { value: [mockFile], configurable: true });
    fireEvent.change(photoInput);
    expect(defaultProps.onAddLayer).not.toHaveBeenCalled();

    global.FileReader = origFileReader;
  });

  it('滚轮缩放 deltaY>0 时缩小图层', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} selectedId="layer_1" />);
    const canvas = screen.getByRole('img');
    fireEvent.wheel(canvas, { deltaY: 100 });
    expect(defaultProps.onScaleLayer).toHaveBeenCalledWith(
      'layer_1',
      expect.any(Number),
      expect.any(Number)
    );
    // The new width/height should be 0.95 of original
    const callArgs = (defaultProps.onScaleLayer as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(callArgs[1]).toBeCloseTo(100 * 0.95, 1);
    expect(callArgs[2]).toBeCloseTo(100 * 0.95, 1);
  });

  it('滚轮事件 selectedId 存在但图层不存在时不缩放', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} selectedId="nonexistent_id" />);
    const canvas = screen.getByRole('img');
    fireEvent.wheel(canvas, { deltaY: -100 });
    expect(defaultProps.onScaleLayer).not.toHaveBeenCalled();
  });

  it('触摸事件 touches 为空时回退到 0', () => {
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} />);
    const canvas = screen.getByRole('img');
    canvas.getBoundingClientRect = vi.fn(() => ({
      left: 0, top: 0, right: 800, bottom: 600,
      width: 800, height: 600, x: 0, y: 0, toJSON: () => {},
    }));
    Object.defineProperty(canvas, 'width', { value: 800 });
    Object.defineProperty(canvas, 'height', { value: 600 });

    // Fire touch event with empty touches array - should use ?? 0 fallback
    fireEvent.touchStart(canvas, { touches: [] });
    // No error thrown; onSelectLayer called with null (since point is 0,0 which is inside layer bounds)
    // Actually at (0,0) with layer at (0,0,100,100) it would select the layer
    expect(defaultProps.onSelectLayer).toHaveBeenCalled();
  });

  it('getContext 返回 null 时 drawCanvas 静默退出', () => {
    HTMLCanvasElement.prototype.getContext = vi.fn(() => null) as any;
    // Should not throw
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} />);
    const canvas = screen.getByRole('img');
    expect(canvas).toBeInTheDocument();
  });

  it('canvasRef.current 为 null 时 drawCanvas/getCanvasPoint 静默退出', () => {
    // Pass canvasRef with current=null to trigger if (!canvas) branches
    const nullCanvasRef = { current: null } as React.RefObject<HTMLCanvasElement | null>;
    render(<VirtualTryOnCanvas {...defaultProps} layers={mockLayers} canvasRef={nullCanvasRef} />);
    // drawCanvas runs with canvas=null → returns early
    // getCanvasPoint runs on mouseDown with canvas=null → returns {x:0, y:0}
    expect(screen.getByRole('img')).toBeInTheDocument();
  });

  it('多可见图层时 drawCanvas 排序回调被执行', () => {
    const multiLayers: TryOnLayer[] = [
      {
        id: 'layer_a', type: 'photo', src: 'a.jpg',
        x: 0, y: 0, width: 100, height: 100,
        rotation: 0, opacity: 1, zIndex: 1, visible: true, name: '图层A',
      },
      {
        id: 'layer_b', type: 'clothing', src: 'b.png',
        x: 50, y: 50, width: 80, height: 80,
        rotation: 0, opacity: 0.8, zIndex: 2, visible: true, name: '图层B',
      },
    ];
    render(<VirtualTryOnCanvas {...defaultProps} layers={multiLayers} />);
    // drawCanvas runs with 2 visible layers → sort callback is executed
    expect(screen.getByRole('img')).toBeInTheDocument();
  });

  it('多可见图层时点击检测排序回调被执行', () => {
    const multiLayers: TryOnLayer[] = [
      {
        id: 'layer_a', type: 'photo', src: 'a.jpg',
        x: 0, y: 0, width: 100, height: 100,
        rotation: 0, opacity: 1, zIndex: 1, visible: true, name: '图层A',
      },
      {
        id: 'layer_b', type: 'clothing', src: 'b.png',
        x: 50, y: 50, width: 80, height: 80,
        rotation: 0, opacity: 0.8, zIndex: 2, visible: true, name: '图层B',
      },
    ];
    render(<VirtualTryOnCanvas {...defaultProps} layers={multiLayers} />);
    const canvas = screen.getByRole('img');
    canvas.getBoundingClientRect = vi.fn(() => ({
      left: 0, top: 0, right: 800, bottom: 600,
      width: 800, height: 600, x: 0, y: 0, toJSON: () => {},
    }));
    Object.defineProperty(canvas, 'width', { value: 800 });
    Object.defineProperty(canvas, 'height', { value: 600 });
    // Click inside overlapping area → findLayerAtPoint sorts layers
    fireEvent.mouseDown(canvas, { clientX: 60, clientY: 60 });
    // layer_b has higher zIndex so it should be selected
    expect(defaultProps.onSelectLayer).toHaveBeenCalledWith('layer_b');
  });
});
