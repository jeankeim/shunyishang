/**
 * Canvas 交互 Hook - 管理虚拟试衣画布状态与操作
 */
import { useState, useCallback, useRef } from 'react';

// ============ 类型定义 ============

export type LayerType = 'photo' | 'clothing';

export interface TryOnLayer {
  id: string;
  type: LayerType;
  src: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  opacity: number;
  zIndex: number;
  visible: boolean;
  name: string;
}

interface CanvasSize {
  width: number;
  height: number;
}

interface HistoryEntry {
  layers: TryOnLayer[];
  selectedId: string | null;
}

export interface UseTryOnCanvasReturn {
  layers: TryOnLayer[];
  selectedId: string | null;
  canvasSize: CanvasSize;
  canUndo: boolean;
  canRedo: boolean;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;

  addLayer: (layer: Omit<TryOnLayer, 'id' | 'zIndex'>) => string;
  removeLayer: (id: string) => void;
  selectLayer: (id: string | null) => void;
  moveLayer: (id: string, x: number, y: number) => void;
  scaleLayer: (id: string, width: number, height: number) => void;
  rotateLayer: (id: string, rotation: number) => void;
  setOpacity: (id: string, opacity: number) => void;
  setLayerVisible: (id: string, visible: boolean) => void;
  reorderLayer: (id: string, newZIndex: number) => void;
  setCanvasSize: (size: CanvasSize) => void;
  undo: () => void;
  redo: () => void;
  exportCanvas: () => string | null;
}

// ============ 常量 ============

const MAX_HISTORY = 50;

let layerIdCounter = 0;
function generateLayerId(): string {
  layerIdCounter += 1;
  return `layer_${Date.now()}_${layerIdCounter}`;
}

// ============ Hook ============

export function useTryOnCanvas(): UseTryOnCanvasReturn {
  const [layers, setLayers] = useState<TryOnLayer[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [canvasSize, setCanvasSizeState] = useState<CanvasSize>({ width: 800, height: 600 });

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // 历史栈
  const historyRef = useRef<HistoryEntry[]>([{ layers: [], selectedId: null }]);
  const historyIndexRef = useRef(0);

  const pushHistory = useCallback((newLayers: TryOnLayer[], newSelectedId: string | null) => {
    const entry: HistoryEntry = {
      layers: JSON.parse(JSON.stringify(newLayers)),
      selectedId: newSelectedId,
    };
    const newHistory = historyRef.current.slice(0, historyIndexRef.current + 1);
    newHistory.push(entry);
    if (newHistory.length > MAX_HISTORY) {
      newHistory.shift();
    }
    historyRef.current = newHistory;
    historyIndexRef.current = newHistory.length - 1;
  }, []);

  // 添加图层
  const addLayer = useCallback((layerData: Omit<TryOnLayer, 'id' | 'zIndex'>): string => {
    const id = generateLayerId();
    const maxZ = layers.length > 0 ? Math.max(...layers.map(l => l.zIndex)) : 0;
    const newLayer: TryOnLayer = { ...layerData, id, zIndex: maxZ + 1 };
    const newLayers = [...layers, newLayer];
    setLayers(newLayers);
    setSelectedId(id);
    pushHistory(newLayers, id);
    return id;
  }, [layers, pushHistory]);

  // 删除图层
  const removeLayer = useCallback((id: string) => {
    const newLayers = layers.filter(l => l.id !== id);
    setLayers(newLayers);
    const newSelectedId = selectedId === id ? null : selectedId;
    setSelectedId(newSelectedId);
    pushHistory(newLayers, newSelectedId);
  }, [layers, selectedId, pushHistory]);

  // 选中图层
  const selectLayer = useCallback((id: string | null) => {
    setSelectedId(id);
  }, []);

  // 更新图层的通用方法
  const updateLayer = useCallback((id: string, updates: Partial<TryOnLayer>) => {
    const newLayers = layers.map(l => l.id === id ? { ...l, ...updates } : l);
    setLayers(newLayers);
    pushHistory(newLayers, selectedId);
  }, [layers, selectedId, pushHistory]);

  // 移动图层
  const moveLayer = useCallback((id: string, x: number, y: number) => {
    updateLayer(id, { x, y });
  }, [updateLayer]);

  // 缩放图层
  const scaleLayer = useCallback((id: string, width: number, height: number) => {
    updateLayer(id, { width, height });
  }, [updateLayer]);

  // 旋转图层
  const rotateLayer = useCallback((id: string, rotation: number) => {
    updateLayer(id, { rotation });
  }, [updateLayer]);

  // 设置透明度
  const setOpacity = useCallback((id: string, opacity: number) => {
    const clamped = Math.max(0, Math.min(1, opacity));
    updateLayer(id, { opacity: clamped });
  }, [updateLayer]);

  // 设置图层可见性
  const setLayerVisible = useCallback((id: string, visible: boolean) => {
    updateLayer(id, { visible });
  }, [updateLayer]);

  // 重排序图层
  const reorderLayer = useCallback((id: string, newZIndex: number) => {
    const newLayers = layers.map(l => l.id === id ? { ...l, zIndex: newZIndex } : l);
    setLayers(newLayers);
    pushHistory(newLayers, selectedId);
  }, [layers, selectedId, pushHistory]);

  // 设置画布尺寸
  const setCanvasSize = useCallback((size: CanvasSize) => {
    setCanvasSizeState(size);
  }, []);

  // 撤销
  const undo = useCallback(() => {
    if (historyIndexRef.current <= 0) return;
    historyIndexRef.current -= 1;
    const entry = historyRef.current[historyIndexRef.current];
    setLayers(JSON.parse(JSON.stringify(entry.layers)));
    setSelectedId(entry.selectedId);
  }, []);

  // 重做
  const redo = useCallback(() => {
    if (historyIndexRef.current >= historyRef.current.length - 1) return;
    historyIndexRef.current += 1;
    const entry = historyRef.current[historyIndexRef.current];
    setLayers(JSON.parse(JSON.stringify(entry.layers)));
    setSelectedId(entry.selectedId);
  }, []);

  // 导出 canvas 为 base64
  const exportCanvas = useCallback((): string | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    return canvas.toDataURL('image/png');
  }, []);

  return {
    layers,
    selectedId,
    canvasSize,
    canUndo: historyIndexRef.current > 0,
    canRedo: historyIndexRef.current < historyRef.current.length - 1,
    canvasRef,
    addLayer,
    removeLayer,
    selectLayer,
    moveLayer,
    scaleLayer,
    rotateLayer,
    setOpacity,
    setLayerVisible,
    reorderLayer,
    setCanvasSize,
    undo,
    redo,
    exportCanvas,
  };
}
