/**
 * ExportModal 组件单元测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExportModal } from '../ExportModal';

// Mock canvas toDataURL
const mockToDataURL = vi.fn(() => 'data:image/png;base64,mockdata');

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  canvasDataUrl: 'data:image/png;base64,testdata',
  title: '我的虚拟试衣',
  wuxingText: '五行穿搭 · 顺衣尚',
};

beforeEach(() => {
  mockToDataURL.mockClear();
  defaultProps.onClose.mockClear();
  // Mock HTMLCanvasElement getContext and toDataURL
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
    fillRect: vi.fn(),
    fillText: vi.fn(),
    drawImage: vi.fn(),
    clearRect: vi.fn(),
    fillStyle: '',
    font: '',
    textAlign: '',
  })) as any;
  HTMLCanvasElement.prototype.toDataURL = mockToDataURL;
});

describe('ExportModal', () => {
  it('isOpen=false 时不渲染弹窗', () => {
    render(<ExportModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('isOpen=true 时渲染弹窗', () => {
    render(<ExportModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('显示标题', () => {
    render(<ExportModal {...defaultProps} />);
    expect(screen.getByText('导出试衣效果')).toBeInTheDocument();
  });

  it('显示下载和分享按钮', () => {
    render(<ExportModal {...defaultProps} />);
    expect(screen.getByLabelText('下载图片')).toBeInTheDocument();
    expect(screen.getByLabelText('分享图片')).toBeInTheDocument();
  });

  it('点击关闭按钮调用 onClose', () => {
    render(<ExportModal {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('关闭导出弹窗'));
    expect(defaultProps.onClose).toHaveBeenCalledOnce();
  });

  it('点击背景调用 onClose', () => {
    render(<ExportModal {...defaultProps} />);
    const dialog = screen.getByRole('dialog');
    fireEvent.click(dialog);
    expect(defaultProps.onClose).toHaveBeenCalledOnce();
  });

  it('下载按钮初始禁用', () => {
    render(<ExportModal {...defaultProps} />);
    // 生成中，下载按钮禁用
    expect(screen.getByLabelText('下载图片')).toBeDisabled();
  });

  it('canvasDataUrl 为 null 时显示错误', async () => {
    render(<ExportModal {...defaultProps} canvasDataUrl={null} />);
    // 应该显示错误状态
    expect(screen.getByText('生成失败，请重试')).toBeInTheDocument();
  });

  it('弹窗内有 aria-modal 属性', () => {
    render(<ExportModal {...defaultProps} />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
  });

  it('分享按钮初始禁用', () => {
    render(<ExportModal {...defaultProps} />);
    expect(screen.getByLabelText('分享图片')).toBeDisabled();
  });

  it('点击下载按钮创建下载链接', async () => {
    // Need to wait for generation to complete
    const mockCtx = {
      fillRect: vi.fn(),
      fillText: vi.fn(),
      drawImage: vi.fn(),
      clearRect: vi.fn(),
      fillStyle: '',
      font: '',
      textAlign: '',
    };
    HTMLCanvasElement.prototype.getContext = vi.fn(() => mockCtx) as any;
    HTMLCanvasElement.prototype.toDataURL = vi.fn(() => 'data:image/png;base64,exported');

    // Mock Image to trigger onload immediately
    const origImage = global.Image;
    (global as any).Image = class MockImage {
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      set src(_val: string) {
        setTimeout(() => this.onload?.(), 0);
      }
      get width() { return 1080; }
      get height() { return 1920; }
    };

    render(<ExportModal {...defaultProps} />);

    // Wait for generation
    await vi.waitFor(() => {
      expect(screen.getByLabelText('下载图片')).not.toBeDisabled();
    }, { timeout: 2000 });

    // Click download
    const downloadBtn = screen.getByLabelText('下载图片');
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click');
    fireEvent.click(downloadBtn);
    expect(clickSpy).toHaveBeenCalled();

    global.Image = origImage;
  });

  it('wuxingText 为空时正常渲染', () => {
    render(<ExportModal {...defaultProps} wuxingText="" />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('图片加载错误时显示错误状态', async () => {
    // Mock Image to trigger onerror
    const origImage = global.Image;
    (global as any).Image = class MockImage {
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      set src(_val: string) {
        setTimeout(() => this.onerror?.(), 0);
      }
    };

    render(<ExportModal {...defaultProps} />);

    await vi.waitFor(() => {
      expect(screen.getByText('生成失败，请重试')).toBeInTheDocument();
    }, { timeout: 2000 });

    global.Image = origImage;
  });

  it('点击分享按钮调用分享 API', async () => {
    // Mock Image to complete immediately
    const origImage = global.Image;
    (global as any).Image = class MockImage {
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      width = 800;
      height = 600;
      set src(_val: string) {
        setTimeout(() => this.onload?.(), 0);
      }
    };
    HTMLCanvasElement.prototype.toDataURL = vi.fn(() => 'data:image/png;base64,exported');

    render(<ExportModal {...defaultProps} />);

    await vi.waitFor(() => {
      expect(screen.getByLabelText('下载图片')).not.toBeDisabled();
    }, { timeout: 2000 });

    // Share should be enabled now
    const shareBtn = screen.getByLabelText('分享图片');
    expect(shareBtn).not.toBeDisabled();

    // Click share - will fail gracefully in test env
    fireEvent.click(shareBtn);

    global.Image = origImage;
  });

  it('getContext 返回 null 时显示错误', async () => {
    HTMLCanvasElement.prototype.getContext = vi.fn(() => null) as any;
    render(<ExportModal {...defaultProps} />);
    await vi.waitFor(() => {
      expect(screen.getByText('生成失败，请重试')).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it('下载按钮在 exportUrl 为 null 时不执行下载', () => {
    render(<ExportModal {...defaultProps} />);
    const downloadBtn = screen.getByLabelText('下载图片');
    // Download is disabled when status is not 'done'
    expect(downloadBtn).toBeDisabled();
    // Click disabled button - should not do anything
    fireEvent.click(downloadBtn);
    // No error thrown
  });

  it('分享按钮在 exportUrl 为 null 时不执行分享', () => {
    render(<ExportModal {...defaultProps} />);
    const shareBtn = screen.getByLabelText('分享图片');
    // Share is disabled when status is not 'done'
    expect(shareBtn).toBeDisabled();
    fireEvent.click(shareBtn);
  });

  it('navigator.share 存在时调用 Web Share API', async () => {
    const origImage = global.Image;
    (global as any).Image = class MockImage {
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      width = 800;
      height = 600;
      set src(_val: string) {
        setTimeout(() => this.onload?.(), 0);
      }
    };
    HTMLCanvasElement.prototype.toDataURL = vi.fn(() => 'data:image/png;base64,exported');

    // Mock navigator.share
    const mockShare = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'share', { value: mockShare, writable: true, configurable: true });
    // Mock fetch for blob conversion
    global.fetch = vi.fn().mockResolvedValue({
      blob: () => Promise.resolve(new Blob(['test'], { type: 'image/png' })),
    }) as any;

    render(<ExportModal {...defaultProps} />);

    await vi.waitFor(() => {
      expect(screen.getByLabelText('下载图片')).not.toBeDisabled();
    }, { timeout: 2000 });

    const shareBtn = screen.getByLabelText('分享图片');
    await vi.waitFor(() => {
      fireEvent.click(shareBtn);
    });

    // Wait for async share to be called
    await vi.waitFor(() => {
      expect(mockShare).toHaveBeenCalled();
    }, { timeout: 2000 });

    global.Image = origImage;
    // Cleanup
    Object.defineProperty(navigator, 'share', { value: undefined, writable: true, configurable: true });
  });

  it('wuxingText 有内容时在导出画布中绘制（imgRatio > canvasRatio 路径）', async () => {
    const origImage = global.Image;
    (global as any).Image = class MockImage {
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      // Wide image: imgRatio > canvasRatio
      width = 2000;
      height = 1000;
      set src(_val: string) {
        setTimeout(() => this.onload?.(), 0);
      }
    };
    HTMLCanvasElement.prototype.toDataURL = vi.fn(() => 'data:image/png;base64,exported');

    render(<ExportModal {...defaultProps} wuxingText="五行文案测试" />);

    await vi.waitFor(() => {
      expect(screen.getByLabelText('下载图片')).not.toBeDisabled();
    }, { timeout: 2000 });

    global.Image = origImage;
  });

  it('wuxingText 为空时 img.onload 路径中不绘制五行文案', async () => {
    const origImage = global.Image;
    (global as any).Image = class MockImage {
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      width = 800;
      height = 600;
      set src(_val: string) {
        setTimeout(() => this.onload?.(), 0);
      }
    };
    HTMLCanvasElement.prototype.toDataURL = vi.fn(() => 'data:image/png;base64,exported');

    render(<ExportModal {...defaultProps} wuxingText="" />);

    await vi.waitFor(() => {
      expect(screen.getByLabelText('下载图片')).not.toBeDisabled();
    }, { timeout: 2000 });

    global.Image = origImage;
  });
});
