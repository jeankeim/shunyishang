/**
 * LayerPanel 组件单元测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LayerPanel } from '../LayerPanel';
import { TryOnLayer } from '../useTryOnCanvas';

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
  {
    id: 'layer_2',
    type: 'clothing',
    src: 'data:image/png;base64,def',
    x: 10,
    y: 10,
    width: 50,
    height: 50,
    rotation: 0,
    opacity: 0.8,
    zIndex: 2,
    visible: true,
    name: '蓝色衬衫',
  },
];

const defaultProps = {
  layers: mockLayers,
  selectedId: null as string | null,
  onSelectLayer: vi.fn(),
  onSetLayerVisible: vi.fn(),
};

describe('LayerPanel', () => {
  beforeEach(() => {
    defaultProps.onSelectLayer.mockClear();
    defaultProps.onSetLayerVisible.mockClear();
  });

  it('渲染空图层提示', () => {
    render(<LayerPanel {...defaultProps} layers={[]} />);
    expect(screen.getByText('暂无图层，请添加照片或衣物')).toBeInTheDocument();
  });

  it('渲染所有图层列表', () => {
    render(<LayerPanel {...defaultProps} />);
    expect(screen.getByText('用户照片')).toBeInTheDocument();
    expect(screen.getByText('蓝色衬衫')).toBeInTheDocument();
  });

  it('显示图层数量', () => {
    render(<LayerPanel {...defaultProps} />);
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('点击图层触发选中回调', () => {
    render(<LayerPanel {...defaultProps} />);
    fireEvent.click(screen.getByText('蓝色衬衫'));
    expect(defaultProps.onSelectLayer).toHaveBeenCalledWith('layer_2');
  });

  it('选中图层有高亮样式', () => {
    render(<LayerPanel {...defaultProps} selectedId="layer_1" />);
    const selectedOption = screen.getByLabelText('图层: 用户照片');
    expect(selectedOption).toHaveAttribute('aria-selected', 'true');
  });

  it('点击可见性按钮触发回调', () => {
    render(<LayerPanel {...defaultProps} />);
    const hideButtons = screen.getAllByLabelText(/隐藏图层/);
    fireEvent.click(hideButtons[0]);
    expect(defaultProps.onSetLayerVisible).toHaveBeenCalledOnce();
  });

  it('隐藏图层显示 EyeOff 图标', () => {
    const hiddenLayers = mockLayers.map(l => ({ ...l, visible: false }));
    render(<LayerPanel {...defaultProps} layers={hiddenLayers} />);
    const showButtons = screen.getAllByLabelText(/显示图层/);
    expect(showButtons.length).toBe(2);
  });

  it('图层按 zIndex 降序排列', () => {
    render(<LayerPanel {...defaultProps} />);
    const options = screen.getAllByRole('option');
    // layer_2 (zIndex 2) should come before layer_1 (zIndex 1)
    expect(options[0]).toHaveAttribute('aria-label', '图层: 蓝色衬衫');
    expect(options[1]).toHaveAttribute('aria-label', '图层: 用户照片');
  });

  it('可见性按钮点击不触发图层选中', () => {
    render(<LayerPanel {...defaultProps} />);
    const hideButton = screen.getAllByLabelText(/隐藏图层/)[0];
    fireEvent.click(hideButton);
    expect(defaultProps.onSelectLayer).not.toHaveBeenCalled();
  });

  it('图层 src 为空时显示 emoji 占位符（photo 类型）', () => {
    const noSrcLayers: TryOnLayer[] = [
      {
        id: 'layer_nosrc_photo',
        type: 'photo',
        src: '',
        x: 0, y: 0, width: 100, height: 100,
        rotation: 0, opacity: 1, zIndex: 1, visible: true,
        name: '无源照片',
      },
    ];
    render(<LayerPanel {...defaultProps} layers={noSrcLayers} />);
    expect(screen.getByText('📷')).toBeInTheDocument();
  });

  it('图层 src 为空时显示 emoji 占位符（clothing 类型）', () => {
    const noSrcLayers: TryOnLayer[] = [
      {
        id: 'layer_nosrc_clothing',
        type: 'clothing',
        src: '',
        x: 0, y: 0, width: 100, height: 100,
        rotation: 0, opacity: 1, zIndex: 1, visible: true,
        name: '无源衣物',
      },
    ];
    render(<LayerPanel {...defaultProps} layers={noSrcLayers} />);
    expect(screen.getByText('👔')).toBeInTheDocument();
  });
});
