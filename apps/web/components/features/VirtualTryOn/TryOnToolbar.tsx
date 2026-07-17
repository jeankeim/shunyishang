'use client'

/**
 * TryOnToolbar - 工具栏组件
 * 包含所有操作按钮和透明度滑块
 */
import React from 'react';
import { motion } from 'framer-motion';
import {
  Upload,
  Shirt,
  RotateCcw,
  RotateCw,
  ArrowUp,
  ArrowDown,
  Trash2,
  Undo2,
  Redo2,
  Download,
} from 'lucide-react';

interface TryOnToolbarProps {
  hasSelection: boolean;
  canUndo: boolean;
  canRedo: boolean;
  opacity: number;
  onAddPhoto: () => void;
  onAddClothing: () => void;
  onRotateLeft: () => void;
  onRotateRight: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onDelete: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onOpacityChange: (value: number) => void;
  onExport: () => void;
}

interface ToolButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  variant?: 'default' | 'danger' | 'primary';
}

function ToolButton({ icon, label, onClick, disabled = false, variant = 'default' }: ToolButtonProps) {
  const colorMap = {
    default: 'text-[var(--brand-body)] hover:bg-[var(--brand-surface)]',
    danger: 'text-[var(--wuxing-fire)] hover:bg-red-50',
    primary: 'text-white bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] hover:opacity-90',
  };

  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : 1.05 }}
      whileTap={{ scale: disabled ? 1 : 0.95 }}
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center justify-center w-10 h-10 rounded-xl transition-colors duration-200 ${colorMap[variant]} ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
      title={label}
      aria-label={label}
    >
      {icon}
    </motion.button>
  );
}

export function TryOnToolbar({
  hasSelection,
  canUndo,
  canRedo,
  opacity,
  onAddPhoto,
  onAddClothing,
  onRotateLeft,
  onRotateRight,
  onMoveUp,
  onMoveDown,
  onDelete,
  onUndo,
  onRedo,
  onOpacityChange,
  onExport,
}: TryOnToolbarProps) {
  return (
    <div
      className="flex flex-col gap-3 p-3 bg-white/95 backdrop-blur-xl rounded-2xl border border-[var(--brand-border)]/60 shadow-lg md:flex-col md:w-14 md:py-4"
      role="toolbar"
      aria-label="试衣工具栏"
    >
      {/* 添加类按钮 */}
      <div className="flex md:flex-col gap-1.5">
        <ToolButton
          icon={<Upload className="w-5 h-5" />}
          label="添加照片"
          onClick={onAddPhoto}
        />
        <ToolButton
          icon={<Shirt className="w-5 h-5" />}
          label="添加衣物"
          onClick={onAddClothing}
        />
      </div>

      {/* 分隔线 */}
      <div className="h-px md:h-auto md:w-full bg-[var(--brand-border)]/60 mx-1 hidden md:block" />
      <div className="w-px md:hidden bg-[var(--brand-border)]/60 my-1" />

      {/* 变换类按钮 */}
      <div className="flex md:flex-col gap-1.5">
        <ToolButton
          icon={<RotateCcw className="w-5 h-5" />}
          label="向左旋转"
          onClick={onRotateLeft}
          disabled={!hasSelection}
        />
        <ToolButton
          icon={<RotateCw className="w-5 h-5" />}
          label="向右旋转"
          onClick={onRotateRight}
          disabled={!hasSelection}
        />
      </div>

      <div className="w-px md:hidden bg-[var(--brand-border)]/60 my-1" />
      <div className="h-px md:h-auto md:w-full bg-[var(--brand-border)]/60 mx-1 hidden md:block" />

      {/* 图层操作 */}
      <div className="flex md:flex-col gap-1.5">
        <ToolButton
          icon={<ArrowUp className="w-5 h-5" />}
          label="图层上移"
          onClick={onMoveUp}
          disabled={!hasSelection}
        />
        <ToolButton
          icon={<ArrowDown className="w-5 h-5" />}
          label="图层下移"
          onClick={onMoveDown}
          disabled={!hasSelection}
        />
        <ToolButton
          icon={<Trash2 className="w-5 h-5" />}
          label="删除图层"
          onClick={onDelete}
          disabled={!hasSelection}
          variant="danger"
        />
      </div>

      <div className="w-px md:hidden bg-[var(--brand-border)]/60 my-1" />
      <div className="h-px md:h-auto md:w-full bg-[var(--brand-border)]/60 mx-1 hidden md:block" />

      {/* 撤销/重做 */}
      <div className="flex md:flex-col gap-1.5">
        <ToolButton
          icon={<Undo2 className="w-5 h-5" />}
          label="撤销"
          onClick={onUndo}
          disabled={!canUndo}
        />
        <ToolButton
          icon={<Redo2 className="w-5 h-5" />}
          label="重做"
          onClick={onRedo}
          disabled={!canRedo}
        />
      </div>

      <div className="w-px md:hidden bg-[var(--brand-border)]/60 my-1" />
      <div className="h-px md:h-auto md:w-full bg-[var(--brand-border)]/60 mx-1 hidden md:block" />

      {/* 透明度滑块 */}
      <div className="flex md:flex-col items-center gap-2 px-1">
        <label htmlFor="opacity-slider" className="text-xs text-[var(--brand-subtle)] font-medium whitespace-nowrap md:writing-mode-vertical">
          透明度
        </label>
        <input
          id="opacity-slider"
          type="range"
          min="0"
          max="100"
          value={Math.round(opacity * 100)}
          onChange={(e) => onOpacityChange(Number(e.target.value) / 100)}
          disabled={!hasSelection}
          className="w-20 md:w-10 h-1.5 accent-[var(--wuxing-wood)] cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="透明度"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(opacity * 100)}
        />
      </div>

      <div className="w-px md:hidden bg-[var(--brand-border)]/60 my-1" />
      <div className="h-px md:h-auto md:w-full bg-[var(--brand-border)]/60 mx-1 hidden md:block" />

      {/* 导出按钮 */}
      <ToolButton
        icon={<Download className="w-5 h-5" />}
        label="导出图片"
        onClick={onExport}
        variant="primary"
      />
    </div>
  );
}
