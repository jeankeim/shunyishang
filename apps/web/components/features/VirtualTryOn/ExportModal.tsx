'use client'

/**
 * ExportModal - 导出/分享弹窗
 * 将 Canvas 内容导出为图片并提供下载和分享功能
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Download, Share2, Loader2, Check } from 'lucide-react';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  canvasDataUrl: string | null;
  title?: string;
  wuxingText?: string;
}

type ExportStatus = 'idle' | 'generating' | 'done' | 'error';

const EXPORT_WIDTH = 1080;
const EXPORT_HEIGHT = 1920;

export function ExportModal({
  isOpen,
  onClose,
  canvasDataUrl,
  title = '我的虚拟试衣',
  wuxingText = '',
}: ExportModalProps) {
  const [status, setStatus] = useState<ExportStatus>('idle');
  const [exportUrl, setExportUrl] = useState<string | null>(null);
  const exportCanvasRef = useRef<HTMLCanvasElement>(null);

  const generateExport = useCallback(() => {
    if (!canvasDataUrl) {
      setStatus('error');
      return;
    }

    setStatus('generating');

    const canvas = exportCanvasRef.current;
    if (!canvas) {
      setStatus('error');
      return;
    }

    canvas.width = EXPORT_WIDTH;
    canvas.height = EXPORT_HEIGHT;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      setStatus('error');
      return;
    }

    // 背景
    ctx.fillStyle = '#FAFAF8';
    ctx.fillRect(0, 0, EXPORT_WIDTH, EXPORT_HEIGHT);

    // 加载用户图片并绘制
    const img = new Image();
    img.onload = () => {
      // 计算图片缩放以填充画布
      const imgRatio = img.width / img.height;
      const canvasRatio = EXPORT_WIDTH / EXPORT_HEIGHT;
      let drawW: number, drawH: number, drawX: number, drawY: number;

      if (imgRatio > canvasRatio) {
        drawH = EXPORT_HEIGHT;
        drawW = drawH * imgRatio;
        drawX = (EXPORT_WIDTH - drawW) / 2;
        drawY = 0;
      } else {
        drawW = EXPORT_WIDTH;
        drawH = drawW / imgRatio;
        drawX = 0;
        drawY = (EXPORT_HEIGHT - drawH) / 2;
      }

      ctx.drawImage(img, drawX, drawY, drawW, drawH);

      // 底部品牌条
      const barHeight = 160;
      ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
      ctx.fillRect(0, EXPORT_HEIGHT - barHeight, EXPORT_WIDTH, barHeight);

      // 标题
      ctx.fillStyle = '#FFFFFF';
      ctx.font = 'bold 48px "Noto Sans SC", sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(title, EXPORT_WIDTH / 2, EXPORT_HEIGHT - barHeight + 60);

      // 五行文案
      if (wuxingText) {
        ctx.font = '28px "Noto Sans SC", sans-serif';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.fillText(wuxingText, EXPORT_WIDTH / 2, EXPORT_HEIGHT - barHeight + 110);
      }

      // 品牌标识
      ctx.font = '24px "Noto Sans SC", sans-serif';
      ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
      ctx.textAlign = 'right';
      ctx.fillText('顺衣尚 · AI穿搭', EXPORT_WIDTH - 40, EXPORT_HEIGHT - 30);

      const dataUrl = canvas.toDataURL('image/png');
      setExportUrl(dataUrl);
      setStatus('done');
    };

    img.onerror = () => {
      setStatus('error');
    };

    img.src = canvasDataUrl;
  }, [canvasDataUrl, title, wuxingText]);

  useEffect(() => {
    if (isOpen) {
      generateExport();
    } else {
      setStatus('idle');
      setExportUrl(null);
    }
  }, [isOpen, generateExport]);

  const handleDownload = useCallback(() => {
    if (!exportUrl) return;
    const link = document.createElement('a');
    link.download = `tryon_${Date.now()}.png`;
    link.href = exportUrl;
    link.click();
  }, [exportUrl]);

  const handleShare = useCallback(async () => {
    if (!exportUrl) return;
    try {
      // 使用 Web Share API（移动端）
      if (navigator.share) {
        const blob = await (await fetch(exportUrl)).blob();
        const file = new File([blob], 'tryon.png', { type: 'image/png' });
        await navigator.share({ files: [file], title, text: wuxingText });
      } else {
        // 桌面端回退：复制到剪贴板
        const blob = await (await fetch(exportUrl)).blob();
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
      }
    } catch {
      // 用户取消或不支持
    }
  }, [exportUrl, title, wuxingText]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-label="导出试衣图片"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 头部 */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--brand-border)]/60">
              <h2 className="text-base font-semibold text-[var(--brand-heading)]">导出试衣效果</h2>
              <button
                onClick={onClose}
                className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-[var(--brand-surface)] transition-colors"
                aria-label="关闭导出弹窗"
              >
                <X className="w-4 h-4 text-[var(--brand-subtle)]" />
              </button>
            </div>

            {/* 预览区域 */}
            <div className="p-5">
              <div className="aspect-[9/16] w-full rounded-xl overflow-hidden bg-[#F8F9FA] border border-[var(--brand-border)]/50 flex items-center justify-center">
                {status === 'generating' && (
                  <div className="flex flex-col items-center gap-3">
                    <Loader2 className="w-8 h-8 text-[var(--wuxing-wood)] animate-spin" />
                    <span className="text-sm text-[var(--brand-subtle)]">生成中...</span>
                  </div>
                )}
                {status === 'done' && exportUrl && (
                  <img
                    src={exportUrl}
                    alt="试衣导出预览"
                    className="w-full h-full object-contain"
                  />
                )}
                {status === 'error' && (
                  <p className="text-sm text-[var(--wuxing-fire)]">生成失败，请重试</p>
                )}
                {status === 'idle' && (
                  <p className="text-sm text-[var(--brand-subtle)]">准备中...</p>
                )}
              </div>
            </div>

            {/* 操作按钮 */}
            <div className="px-5 pb-5 flex gap-3">
              <button
                onClick={handleDownload}
                disabled={status !== 'done'}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] text-white font-medium shadow-md hover:shadow-lg transition-shadow disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="下载图片"
              >
                {status === 'done' ? <Check className="w-4 h-4" /> : <Download className="w-4 h-4" />}
                下载
              </button>
              <button
                onClick={handleShare}
                disabled={status !== 'done'}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl border-2 border-[var(--brand-border)] text-[var(--brand-heading)] font-medium hover:bg-[var(--brand-surface)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="分享图片"
              >
                <Share2 className="w-4 h-4" />
                分享
              </button>
            </div>
          </motion.div>

          {/* 隐藏的导出画布 */}
          <canvas ref={exportCanvasRef} className="hidden" aria-hidden="true" />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
