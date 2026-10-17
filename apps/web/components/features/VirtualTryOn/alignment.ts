/**
 * 试衣画布的对齐辅助计算
 *
 * 人体是左右对称的，衣物偏离中线是新手最容易出的错，
 * 因此提供一条垂直中线参考 + 拖拽吸附。纯几何计算，便于单测。
 */

/** 吸附判定阈值（画布内坐标像素）：小于该距离就吸到中线 */
export const SNAP_THRESHOLD_PX = 8;

/** 静止态判断容差：允许浮点误差 */
export const CENTER_TOLERANCE_PX = 1;

export interface VerticalSnap {
  /** 吸附后的图层左上角 x */
  x: number;
  /** 本次是否命中吸附（用于高亮辅助线） */
  snapped: boolean;
}

/**
 * 把水平拖拽位置吸附到画布垂直中线
 *
 * @param desiredX   未吸附时的左上角 x
 * @param layerWidth 图层宽度
 * @param canvasWidth 画布宽度
 * @param enabled    吸附开关（辅助线关闭时一并关闭，避免"看不见却被吸住"的怪手感）
 */
export function snapToVerticalCenter(
  desiredX: number,
  layerWidth: number,
  canvasWidth: number,
  enabled = true,
  threshold = SNAP_THRESHOLD_PX,
): VerticalSnap {
  if (!enabled || canvasWidth <= 0 || layerWidth <= 0) {
    return { x: desiredX, snapped: false };
  }
  const midX = canvasWidth / 2;
  const center = desiredX + layerWidth / 2;
  if (Math.abs(center - midX) <= threshold) {
    return { x: midX - layerWidth / 2, snapped: true };
  }
  return { x: desiredX, snapped: false };
}

/** 图层当前是否已与中线对齐（拖拽结束后辅助线仍常亮，给出"放对了"的确认） */
export function isHorizontallyCentered(
  x: number,
  layerWidth: number,
  canvasWidth: number,
  tolerance = CENTER_TOLERANCE_PX,
): boolean {
  if (canvasWidth <= 0 || layerWidth <= 0) return false;
  return Math.abs(x + layerWidth / 2 - canvasWidth / 2) <= tolerance;
}
