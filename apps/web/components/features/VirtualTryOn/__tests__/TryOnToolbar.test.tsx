/**
 * TryOnToolbar 组件单元测试
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TryOnToolbar } from '../TryOnToolbar';

const defaultProps = {
  hasSelection: true,
  canUndo: true,
  canRedo: false,
  opacity: 0.8,
  onAddPhoto: vi.fn(),
  onAddClothing: vi.fn(),
  onRotateLeft: vi.fn(),
  onRotateRight: vi.fn(),
  onMoveUp: vi.fn(),
  onMoveDown: vi.fn(),
  onDelete: vi.fn(),
  onUndo: vi.fn(),
  onRedo: vi.fn(),
  onOpacityChange: vi.fn(),
  onExport: vi.fn(),
};

describe('TryOnToolbar', () => {
  it('渲染所有工具按钮', () => {
    render(<TryOnToolbar {...defaultProps} />);
    expect(screen.getByLabelText('添加照片')).toBeInTheDocument();
    expect(screen.getByLabelText('添加衣物')).toBeInTheDocument();
    expect(screen.getByLabelText('向左旋转')).toBeInTheDocument();
    expect(screen.getByLabelText('向右旋转')).toBeInTheDocument();
    expect(screen.getByLabelText('图层上移')).toBeInTheDocument();
    expect(screen.getByLabelText('图层下移')).toBeInTheDocument();
    expect(screen.getByLabelText('删除图层')).toBeInTheDocument();
    expect(screen.getByLabelText('撤销')).toBeInTheDocument();
    expect(screen.getByLabelText('重做')).toBeInTheDocument();
    expect(screen.getByLabelText('导出图片')).toBeInTheDocument();
  });

  it('透明度滑块显示正确值', () => {
    render(<TryOnToolbar {...defaultProps} opacity={0.5} />);
    const slider = screen.getByLabelText('透明度');
    expect(slider).toHaveValue('50');
  });

  it('点击添加照片按钮调用回调', () => {
    render(<TryOnToolbar {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('添加照片'));
    expect(defaultProps.onAddPhoto).toHaveBeenCalledOnce();
  });

  it('点击添加衣物按钮调用回调', () => {
    render(<TryOnToolbar {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('添加衣物'));
    expect(defaultProps.onAddClothing).toHaveBeenCalledOnce();
  });

  it('点击旋转按钮调用回调', () => {
    render(<TryOnToolbar {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('向左旋转'));
    expect(defaultProps.onRotateLeft).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByLabelText('向右旋转'));
    expect(defaultProps.onRotateRight).toHaveBeenCalledOnce();
  });

  it('点击图层操作按钮调用回调', () => {
    render(<TryOnToolbar {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('图层上移'));
    expect(defaultProps.onMoveUp).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByLabelText('图层下移'));
    expect(defaultProps.onMoveDown).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByLabelText('删除图层'));
    expect(defaultProps.onDelete).toHaveBeenCalledOnce();
  });

  it('点击撤销/重做按钮调用回调', () => {
    render(<TryOnToolbar {...defaultProps} canRedo={true} />);
    fireEvent.click(screen.getByLabelText('撤销'));
    expect(defaultProps.onUndo).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByLabelText('重做'));
    expect(defaultProps.onRedo).toHaveBeenCalledOnce();
  });

  it('没有选中时操作按钮禁用', () => {
    render(<TryOnToolbar {...defaultProps} hasSelection={false} />);
    expect(screen.getByLabelText('向左旋转')).toBeDisabled();
    expect(screen.getByLabelText('向右旋转')).toBeDisabled();
    expect(screen.getByLabelText('图层上移')).toBeDisabled();
    expect(screen.getByLabelText('图层下移')).toBeDisabled();
    expect(screen.getByLabelText('删除图层')).toBeDisabled();
  });

  it('不能撤销时撤销按钮禁用', () => {
    render(<TryOnToolbar {...defaultProps} canUndo={false} />);
    expect(screen.getByLabelText('撤销')).toBeDisabled();
  });

  it('不能重做时重做按钮禁用', () => {
    render(<TryOnToolbar {...defaultProps} canRedo={false} />);
    expect(screen.getByLabelText('重做')).toBeDisabled();
  });

  it('透明度滑块变化时调用回调', () => {
    render(<TryOnToolbar {...defaultProps} />);
    const slider = screen.getByLabelText('透明度');
    fireEvent.change(slider, { target: { value: '75' } });
    expect(defaultProps.onOpacityChange).toHaveBeenCalledWith(0.75);
  });

  it('点击导出按钮调用回调', () => {
    render(<TryOnToolbar {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('导出图片'));
    expect(defaultProps.onExport).toHaveBeenCalledOnce();
  });

  it('toolbar 有正确的 role 属性', () => {
    render(<TryOnToolbar {...defaultProps} />);
    expect(screen.getByRole('toolbar')).toBeInTheDocument();
  });
});
