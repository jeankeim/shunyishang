'use client'

/**
 * VirtualTryOnCanvas - Canvas 画布主组件
 * 支持上传照片、叠加衣物图层、拖拽/缩放/旋转交互，以及中线对齐辅助线
 */
import React, { useEffect, useRef, useCallback, useState } from 'react';
import { motion } from 'framer-motion';
import { Camera, Upload } from 'lucide-react';
import { TryOnLayer } from './useTryOnCanvas';
import { snapToVerticalCenter, isHorizontallyCentered } from './alignment';
import { cn } from '@/lib/utils';

interface VirtualTryOnCanvasProps {
  layers: TryOnLayer[];
  selectedId: string | null;
  canvasSize: { width: number; height: number };
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  onSelectLayer: (id: string | null) => void;
  onMoveLayer: (id: string, x: number, y: number) => void;
  onScaleLayer: (id: string, width: number, height: number) => void;
  onRotateLayer: (id: string, rotation: number) => void;
  onAddLayer: (layer: Omit<TryOnLayer, 'id' | 'zIndex'>) => string;
  onSetCanvasSize: (size: { width: number; height: number }) => void;
  /** 中线辅助线 + 吸附开关（默认开） */
  showGuides?: boolean;
}

export function VirtualTryOnCanvas({
  layers,
  selectedId,
  canvasSize,
  canvasRef,
  onSelectLayer,
  onMoveLayer,
  onScaleLayer,
  onRotateLayer,
  onAddLayer,
  onSetCanvasSize,
  showGuides = true,
}: VirtualTryOnCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const dragStateRef = useRef<{
    isDragging: boolean;
    layerId: string | null;
    startX: number;
    startY: number;
    layerStartX: number;
    layerStartY: number;
    layerWidth: number;
  }>({ isDragging: false, layerId: null, startX: 0, startY: 0, layerStartX: 0, layerStartY: 0, layerWidth: 0 });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const clothingInputRef = useRef<HTMLInputElement>(null);

  // 图层图片缓存：src 为 data URL，每帧重建会闪烁且卡顿
  const imageCacheRef = useRef<Map<string, HTMLImageElement>>(new Map());
  // 图片异步解码完成后递增此计数器触发重绘（否则首帧只能画背景）
  const [imagesVersion, setImagesVersion] = useState(0);
  // 拖拽中是否正处于吸附态（高亮辅助线）
  const [snapActive, setSnapActive] = useState(false);

  // 取已解码完成的图层图片；未就绪时返回 null（ onload 后通过 imagesVersion 触发重绘）
  const getReadyImage = useCallback((src: string): HTMLImageElement | null => {
    if (!src) return null;
    const cache = imageCacheRef.current;
    const cached = cache.get(src);
    if (cached) return cached.complete && cached.naturalWidth > 0 ? cached : null;

    const img = new Image();
    img.onload = () => setImagesVersion(v => v + 1);
    img.onerror = () => cache.delete(src);
    cache.set(src, img);
    img.src = src;
    return null;
  }, []);

  // 绘制 canvas
  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = canvasSize.width;
    canvas.height = canvasSize.height;

    // 清空画布
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 背景
    ctx.fillStyle = '#F8F9FA';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 按 zIndex 排序图层
    const sortedLayers = [...layers].filter(l => l.visible).sort((a, b) => a.zIndex - b.zIndex);

    sortedLayers.forEach(layer => {
      ctx.save();
      ctx.globalAlpha = layer.opacity;

      const centerX = layer.x + layer.width / 2;
      const centerY = layer.y + layer.height / 2;

      ctx.translate(centerX, centerY);
      ctx.rotate((layer.rotation * Math.PI) / 180);

      // 图层图片本体（旧实现只画了背景与选中框，衣物传进来后预览区看不到任何图）
      const img = getReadyImage(layer.src);
      if (img && typeof ctx.drawImage === 'function') {
        ctx.drawImage(img, -layer.width / 2, -layer.height / 2, layer.width, layer.height);
      }

      // 选中状态高亮 (--wuxing-wood = #3DA35D)
      if (layer.id === selectedId) {
        ctx.strokeStyle = '#3DA35D';
        ctx.lineWidth = 3;
        ctx.setLineDash([6, 3]);
        ctx.strokeRect(-layer.width / 2 - 4, -layer.height / 2 - 4, layer.width + 8, layer.height + 8);
        ctx.setLineDash([]);
      }

      ctx.restore();
    });
  }, [layers, selectedId, canvasSize, canvasRef, getReadyImage]);

  useEffect(() => {
    drawCanvas();
    // 清理已删除图层的图片缓存：data URL 很大，不能让它们常驻内存
    const cache = imageCacheRef.current;
    const active = new Set(layers.map(l => l.src));
    cache.forEach((_, src) => {
      if (!active.has(src)) cache.delete(src);
    });
  }, [drawCanvas, imagesVersion, layers]);

  // 响应式画布尺寸
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          onSetCanvasSize({ width: Math.floor(width), height: Math.floor(height) });
        }
      }
    });

    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, [onSetCanvasSize]);

  // 查找点击位置的图层
  const findLayerAtPoint = useCallback((px: number, py: number): TryOnLayer | null => {
    const sorted = [...layers].filter(l => l.visible).sort((a, b) => b.zIndex - a.zIndex);
    for (const layer of sorted) {
      if (
        px >= layer.x && px <= layer.x + layer.width &&
        py >= layer.y && py <= layer.y + layer.height
      ) {
        return layer;
      }
    }
    return null;
  }, [layers]);

  // 鼠标/触摸事件处理
  const getCanvasPoint = useCallback((e: React.MouseEvent | React.TouchEvent): { x: number; y: number } => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const clientX = 'touches' in e ? e.touches[0]?.clientX ?? 0 : e.clientX;
    const clientY = 'touches' in e ? e.touches[0]?.clientY ?? 0 : e.clientY;
    return {
      x: (clientX - rect.left) * (canvas.width / rect.width),
      y: (clientY - rect.top) * (canvas.height / rect.height),
    };
  }, [canvasRef]);

  const handlePointerDown = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    const point = getCanvasPoint(e);
    const layer = findLayerAtPoint(point.x, point.y);
    if (layer) {
      onSelectLayer(layer.id);
      dragStateRef.current = {
        isDragging: true,
        layerId: layer.id,
        startX: point.x,
        startY: point.y,
        layerStartX: layer.x,
        layerStartY: layer.y,
        layerWidth: layer.width,
      };
    } else {
      onSelectLayer(null);
    }
  }, [getCanvasPoint, findLayerAtPoint, onSelectLayer]);

  const handlePointerMove = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    const state = dragStateRef.current;
    if (!state.isDragging || !state.layerId) return;
    const point = getCanvasPoint(e);
    const dx = point.x - state.startX;
    const dy = point.y - state.startY;
    // 水平方向经过中线吸附（底图照片不参与，否则会把人弄歪）；垂直方向不吸附
    const isClothing = state.layerId !== null
      && layers.find(l => l.id === state.layerId)?.type === 'clothing';
    const { x, snapped } = snapToVerticalCenter(
      state.layerStartX + dx,
      state.layerWidth,
      canvasSize.width,
      showGuides && isClothing,
    );
    setSnapActive(prev => (prev === snapped ? prev : snapped));
    onMoveLayer(state.layerId, x, state.layerStartY + dy);
  }, [getCanvasPoint, onMoveLayer, canvasSize.width, showGuides, layers]);

  const handlePointerUp = useCallback(() => {
    dragStateRef.current.isDragging = false;
    dragStateRef.current.layerId = null;
    setSnapActive(false);
  }, []);

  // 鼠标滚轮缩放
  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (!selectedId) return;
    const selectedLayer = layers.find(l => l.id === selectedId);
    if (!selectedLayer) return;
    e.preventDefault();
    const scaleFactor = e.deltaY > 0 ? 0.95 : 1.05;
    const newW = Math.max(20, selectedLayer.width * scaleFactor);
    const newH = Math.max(20, selectedLayer.height * scaleFactor);
    onScaleLayer(selectedId, newW, newH);
  }, [selectedId, layers, onScaleLayer]);

  // 上传照片
  const handlePhotoUpload = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleClothingUpload = useCallback(() => {
    clothingInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>, type: 'photo' | 'clothing') => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const src = ev.target?.result as string;
      if (!src) return;
      const img = new Image();
      img.onload = () => {
        const maxW = canvasSize.width * 0.6;
        const maxH = canvasSize.height * 0.6;
        let w = img.width;
        let h = img.height;
        const ratio = Math.min(maxW / w, maxH / h, 1);
        w *= ratio;
        h *= ratio;
        onAddLayer({
          type,
          src,
          x: (canvasSize.width - w) / 2,
          y: (canvasSize.height - h) / 2,
          width: w,
          height: h,
          rotation: 0,
          opacity: 1,
          visible: true,
          name: type === 'photo' ? '用户照片' : file.name.replace(/\.\w+$/, ''),
        });
      };
      img.src = src;
    };
    reader.readAsDataURL(file);
    // 重置 input 以便重复选择同一文件
    e.target.value = '';
  }, [canvasSize, onAddLayer]);

  const hasPhoto = layers.some(l => l.type === 'photo');

  // 选中衣物是否已居中：拖拽结束后辅助线仍常亮，给出确认感
  const selectedLayer = layers.find(l => l.id === selectedId);
  const isCentered = !!selectedLayer
    && selectedLayer.type === 'clothing'
    && isHorizontallyCentered(selectedLayer.x, selectedLayer.width, canvasSize.width);
  const guideHighlight = snapActive || isCentered;

  return (
    <div className="relative flex-1 min-h-0 w-full flex flex-col items-center" ref={containerRef}>
      {/* 空状态提示 */}
      {layers.length === 0 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="absolute inset-0 flex flex-col items-center justify-center z-10 bg-[#F8F9FA] rounded-xl"
        >
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[var(--wuxing-wood)]/20 to-[var(--wuxing-water)]/20 flex items-center justify-center mb-4">
            <Camera className="w-10 h-10 text-[var(--wuxing-wood)]" />
          </div>
          <h3 className="text-lg font-semibold text-[var(--brand-heading)] mb-2">开始虚拟试衣</h3>
          <p className="text-sm text-[var(--brand-subtle)] mb-6 text-center max-w-xs">
            上传你的照片作为底图，然后添加衣物进行搭配
          </p>
          <button
            onClick={handlePhotoUpload}
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] text-white font-medium shadow-md hover:shadow-lg transition-shadow"
            aria-label="上传照片"
          >
            <Upload className="w-5 h-5" />
            上传照片
          </button>
        </motion.div>
      )}

      {/* Canvas 画布 */}
      <canvas
        ref={canvasRef}
        className="flex-1 min-h-0 w-full rounded-xl cursor-crosshair block"
        style={{ touchAction: 'none' }}
        onMouseDown={handlePointerDown}
        onMouseMove={handlePointerMove}
        onMouseUp={handlePointerUp}
        onMouseLeave={handlePointerUp}
        onTouchStart={handlePointerDown}
        onTouchMove={handlePointerMove}
        onTouchEnd={handlePointerUp}
        onWheel={handleWheel}
        aria-label="虚拟试衣画布"
        role="img"
      />

      {/* 中线对齐辅助层：用 DOM 叠加而不是画在 canvas 上，保证导出成图不带辅助线 */}
      {showGuides && layers.length > 0 && (
        <div
          aria-hidden="true"
          data-testid="alignment-guides"
          className="pointer-events-none absolute inset-0 z-20"
        >
          <div
            className={cn(
              'absolute top-0 bottom-0 left-1/2 -translate-x-1/2 border-l border-dashed transition-colors',
              guideHighlight ? 'border-[var(--wuxing-wood)]' : 'border-stone-400/50'
            )}
          />
          {guideHighlight && (
            <span className="absolute left-1/2 top-3 -translate-x-1/2 rounded-full bg-[var(--wuxing-wood)] px-2 py-0.5 text-[10px] font-medium text-white">
              已对齐中线
            </span>
          )}
        </div>
      )}

      {/* 添加衣物浮动按钮（有照片时显示） */}
      {hasPhoto && (
        <motion.button
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          onClick={handleClothingUpload}
          className="absolute bottom-4 right-4 flex items-center gap-2 px-4 py-2 rounded-xl bg-white/90 backdrop-blur-sm border border-[var(--brand-border)] shadow-md hover:shadow-lg transition-shadow text-sm font-medium text-[var(--brand-heading)]"
          aria-label="添加衣物"
        >
          <Upload className="w-4 h-4 text-[var(--wuxing-wood)]" />
          添加衣物
        </motion.button>
      )}

      {/* 隐藏的文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => handleFileChange(e, 'photo')}
        aria-label="选择照片文件"
      />
      <input
        ref={clothingInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => handleFileChange(e, 'clothing')}
        aria-label="选择衣物文件"
      />
    </div>
  );
}
