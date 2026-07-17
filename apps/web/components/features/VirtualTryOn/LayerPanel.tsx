'use client'

/**
 * LayerPanel - 图层管理面板
 * 显示图层列表、支持选中/显示隐藏
 */
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, EyeOff, Layers } from 'lucide-react';
import { TryOnLayer } from './useTryOnCanvas';

interface LayerPanelProps {
  layers: TryOnLayer[];
  selectedId: string | null;
  onSelectLayer: (id: string | null) => void;
  onSetLayerVisible: (id: string, visible: boolean) => void;
}

export function LayerPanel({
  layers,
  selectedId,
  onSelectLayer,
  onSetLayerVisible,
}: LayerPanelProps) {
  // 按 zIndex 降序排列（上层在前）
  const sortedLayers = [...layers].sort((a, b) => b.zIndex - a.zIndex);

  if (layers.length === 0) {
    return (
      <div className="p-4 bg-white/95 backdrop-blur-xl rounded-2xl border border-[var(--brand-border)]/60 shadow-lg">
        <div className="flex items-center gap-2 mb-3">
          <Layers className="w-4 h-4 text-[var(--wuxing-wood)]" />
          <h3 className="text-sm font-semibold text-[var(--brand-heading)]">图层</h3>
        </div>
        <p className="text-xs text-[var(--brand-subtle)] text-center py-4">暂无图层，请添加照片或衣物</p>
      </div>
    );
  }

  return (
    <div className="p-3 bg-white/95 backdrop-blur-xl rounded-2xl border border-[var(--brand-border)]/60 shadow-lg max-h-60 overflow-y-auto">
      <div className="flex items-center gap-2 mb-2 px-1">
        <Layers className="w-4 h-4 text-[var(--wuxing-wood)]" />
        <h3 className="text-sm font-semibold text-[var(--brand-heading)]">图层</h3>
        <span className="text-xs text-[var(--brand-subtle)] ml-auto">{layers.length}</span>
      </div>

      <div className="space-y-1" role="listbox" aria-label="图层列表">
        <AnimatePresence>
          {sortedLayers.map((layer) => {
            const isSelected = layer.id === selectedId;
            return (
              <motion.div
                key={layer.id}
                layout
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.15 }}
                onClick={() => onSelectLayer(layer.id)}
                className={`flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors duration-150 ${
                  isSelected
                    ? 'bg-[var(--brand-surface)] border border-[var(--wuxing-wood)]/30'
                    : 'hover:bg-[var(--brand-surface)] border border-transparent'
                }`}
                role="option"
                aria-selected={isSelected}
                aria-label={`图层: ${layer.name}`}
              >
                {/* 缩略图 */}
                <div className="w-8 h-8 rounded-md overflow-hidden bg-[var(--brand-surface)] flex-shrink-0 border border-[var(--brand-border)]/50">
                  {layer.src ? (
                    <img
                      src={layer.src}
                      alt={layer.name}
                      className="w-full h-full object-cover"
                      style={{ opacity: layer.visible ? 1 : 0.4 }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-xs text-[var(--brand-subtle)]">
                      {layer.type === 'photo' ? '📷' : '👔'}
                    </div>
                  )}
                </div>

                {/* 名称 */}
                <span className={`flex-1 text-xs font-medium truncate ${
                  isSelected ? 'text-[var(--brand-heading)]' : 'text-[var(--brand-body)]'
                }`} style={{ opacity: layer.visible ? 1 : 0.5 }}>
                  {layer.name}
                </span>

                {/* 可见性切换 */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onSetLayerVisible(layer.id, !layer.visible);
                  }}
                  className="w-6 h-6 rounded-md flex items-center justify-center hover:bg-[var(--brand-border)]/50 transition-colors flex-shrink-0"
                  aria-label={layer.visible ? `隐藏图层 ${layer.name}` : `显示图层 ${layer.name}`}
                  title={layer.visible ? '隐藏' : '显示'}
                >
                  {layer.visible ? (
                    <Eye className="w-3.5 h-3.5 text-[var(--brand-subtle)]" />
                  ) : (
                    <EyeOff className="w-3.5 h-3.5 text-[#B0BFB5]" />
                  )}
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
