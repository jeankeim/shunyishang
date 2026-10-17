/**
 * 试衣画布对齐几何 helper 单元测试
 */
import { describe, it, expect } from 'vitest';
import {
  snapToVerticalCenter,
  isHorizontallyCentered,
  SNAP_THRESHOLD_PX,
  CENTER_TOLERANCE_PX,
} from '../alignment';

describe('snapToVerticalCenter', () => {
  it('阈值内吸到中线（左上角 = 中线 - 半宽）', () => {
    // 画布 800 → 中线 400；图层宽 100 → 期望左上角 350
    const result = snapToVerticalCenter(344, 100, 800);
    expect(result).toEqual({ x: 350, snapped: true });
  });

  it('阈值边界（正好等于阈值）仍吸附', () => {
    // desiredX + 50 = 400 - SNAP_THRESHOLD_PX
    const desired = 400 - SNAP_THRESHOLD_PX - 50;
    expect(snapToVerticalCenter(desired, 100, 800)).toEqual({ x: 350, snapped: true });
  });

  it('超出阈值原样返回', () => {
    const desired = 400 - SNAP_THRESHOLD_PX - 50 - 1;
    const result = snapToVerticalCenter(desired, 100, 800);
    expect(result.x).toBe(desired);
    expect(result.snapped).toBe(false);
  });

  it('右侧偏过中线但在阈值内同样吸附（对称）', () => {
    // 左上角 356 → 中心 406，偏过中线 6px < 阈值 8
    expect(snapToVerticalCenter(356, 100, 800)).toEqual({ x: 350, snapped: true });
  });

  it('enabled=false 时直通不吸附（辅助线关闭不该有隐形磁力）', () => {
    expect(snapToVerticalCenter(344, 100, 800, false)).toEqual({ x: 344, snapped: false });
  });

  it('自定义阈值生效', () => {
    // 中心 390 距中线 10：默认阈值不吸，放大到 16 就吸
    expect(snapToVerticalCenter(340, 100, 800).snapped).toBe(false);
    expect(snapToVerticalCenter(340, 100, 800, true, 16).snapped).toBe(true);
  });

  it('非法画布宽度时不吸附（ResizeObserver 未就绪的一帧）', () => {
    expect(snapToVerticalCenter(344, 100, 0)).toEqual({ x: 344, snapped: false });
    expect(snapToVerticalCenter(344, 0, 800)).toEqual({ x: 344, snapped: false });
  });
});

describe('isHorizontallyCentered', () => {
  it('完全居中的图层返回 true', () => {
    expect(isHorizontallyCentered(350, 100, 800)).toBe(true);
  });

  it('容差内的浮点误差仍视为居中', () => {
    expect(isHorizontallyCentered(350 + CENTER_TOLERANCE_PX / 2, 100, 800)).toBe(true);
  });

  it('超出容差返回 false', () => {
    expect(isHorizontallyCentered(344, 100, 800)).toBe(false);
  });

  it('非法宽高返回 false', () => {
    expect(isHorizontallyCentered(350, 100, 0)).toBe(false);
    expect(isHorizontallyCentered(350, 0, 800)).toBe(false);
  });
});
