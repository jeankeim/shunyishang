'use client'

/**
 * 虚拟试衣页面
 * 整合 VirtualTryOnCanvas + TryOnToolbar + LayerPanel
 */
import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';
import {
  VirtualTryOnCanvas,
  TryOnToolbar,
  LayerPanel,
  ExportModal,
  useTryOnCanvas,
} from '@/components/features/VirtualTryOn';

export default function TryOnPage() {
  const {
    layers,
    selectedId,
    canvasSize,
    canUndo,
    canRedo,
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
  } = useTryOnCanvas();

  const [showExportModal, setShowExportModal] = useState(false);
  const [canvasDataUrl, setCanvasDataUrl] = useState<string | null>(null);

  const selectedLayer = layers.find(l => l.id === selectedId);

  // 工具栏回调
  const handleAddPhoto = useCallback(() => {
    // 触发文件输入（通过 canvas 内部的按钮）
    const fileInput = document.querySelector<HTMLInputElement>('input[aria-label="选择照片文件"]');
    fileInput?.click();
  }, []);

  const handleAddClothing = useCallback(() => {
    const clothingInput = document.querySelector<HTMLInputElement>('input[aria-label="选择衣物文件"]');
    clothingInput?.click();
  }, []);

  const handleRotateLeft = useCallback(() => {
    if (!selectedId || !selectedLayer) return;
    rotateLayer(selectedId, selectedLayer.rotation - 15);
  }, [selectedId, selectedLayer, rotateLayer]);

  const handleRotateRight = useCallback(() => {
    if (!selectedId || !selectedLayer) return;
    rotateLayer(selectedId, selectedLayer.rotation + 15);
  }, [selectedId, selectedLayer, rotateLayer]);

  const handleMoveUp = useCallback(() => {
    if (!selectedId || !selectedLayer) return;
    reorderLayer(selectedId, selectedLayer.zIndex + 1);
  }, [selectedId, selectedLayer, reorderLayer]);

  const handleMoveDown = useCallback(() => {
    if (!selectedId || !selectedLayer) return;
    reorderLayer(selectedId, Math.max(0, selectedLayer.zIndex - 1));
  }, [selectedId, selectedLayer, reorderLayer]);

  const handleDelete = useCallback(() => {
    if (!selectedId) return;
    removeLayer(selectedId);
  }, [selectedId, removeLayer]);

  const handleOpacityChange = useCallback((value: number) => {
    if (!selectedId) return;
    setOpacity(selectedId, value);
  }, [selectedId, setOpacity]);

  const handleExport = useCallback(() => {
    const dataUrl = exportCanvas();
    setCanvasDataUrl(dataUrl);
    setShowExportModal(true);
  }, [exportCanvas]);

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FA]" style={{ height: '100dvh' }}>
      {/* 顶部导航栏 */}
      <div className="h-14 flex items-center justify-between px-4 bg-white/90 backdrop-blur-xl border-b border-[#E8F0EB]/60 flex-shrink-0">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => window.history.back()}
          className="flex items-center gap-1.5 text-sm text-[#4A5F52] hover:text-[#2D4A38] transition-colors"
          aria-label="返回上一页"
        >
          <ArrowLeft className="w-4 h-4" />
          返回
        </motion.button>
        <h1 className="text-base font-semibold text-[#2D4A38]">虚拟试衣</h1>
        <div className="w-16" />
      </div>

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden p-3 gap-3">
        {/* 画布区域 */}
        <div className="flex-1 relative rounded-2xl overflow-hidden border border-[#E8F0EB]/60 bg-white shadow-sm min-h-[300px] flex flex-col">
          <VirtualTryOnCanvas
            layers={layers}
            selectedId={selectedId}
            canvasSize={canvasSize}
            canvasRef={canvasRef}
            onSelectLayer={selectLayer}
            onMoveLayer={moveLayer}
            onScaleLayer={scaleLayer}
            onRotateLayer={rotateLayer}
            onAddLayer={addLayer}
            onSetCanvasSize={setCanvasSize}
          />
        </div>

        {/* 右侧工具面板 */}
        <div className="flex md:flex-col gap-3 md:w-64 flex-shrink-0 overflow-y-auto pb-4 md:pb-0">
          {/* 工具栏 */}
          <div className="md:flex-1 overflow-x-auto md:overflow-x-visible">
            <TryOnToolbar
              hasSelection={!!selectedId}
              canUndo={canUndo}
              canRedo={canRedo}
              opacity={selectedLayer?.opacity ?? 1}
              onAddPhoto={handleAddPhoto}
              onAddClothing={handleAddClothing}
              onRotateLeft={handleRotateLeft}
              onRotateRight={handleRotateRight}
              onMoveUp={handleMoveUp}
              onMoveDown={handleMoveDown}
              onDelete={handleDelete}
              onUndo={undo}
              onRedo={redo}
              onOpacityChange={handleOpacityChange}
              onExport={handleExport}
            />
          </div>

          {/* 图层面板 */}
          <LayerPanel
            layers={layers}
            selectedId={selectedId}
            onSelectLayer={selectLayer}
            onSetLayerVisible={setLayerVisible}
          />
        </div>
      </div>

      {/* 导出弹窗 */}
      <ExportModal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        canvasDataUrl={canvasDataUrl}
        title="我的虚拟试衣"
        wuxingText="五行穿搭 · 顺衣尚"
      />
    </div>
  );
}
