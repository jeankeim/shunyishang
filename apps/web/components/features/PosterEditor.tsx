import React from 'react';
import { WUXING_THEMES, ColorTheme } from '@/lib/poster-templates';
import { Edit3, Type, MessageSquare, PenTool, Palette } from 'lucide-react';

interface PosterEditorProps {
  title: string;
  onTitleChange: (title: string) => void;
  quote: string;
  onQuoteChange: (quote: string) => void;
  signature: string;
  onSignatureChange: (signature: string) => void;
  theme: ColorTheme;
  onThemeChange: (theme: ColorTheme) => void;
}

export const PosterEditor: React.FC<PosterEditorProps> = ({
  title,
  onTitleChange,
  quote,
  onQuoteChange,
  signature,
  onSignatureChange,
  theme,
  onThemeChange,
}) => {
  // 输入框通用样式
  const inputBaseStyle = "w-full px-4 py-3 rounded-xl border-2 transition-all duration-200 focus:outline-none focus:ring-0 text-stone-800 placeholder:text-stone-500";
  
  return (
    <div className="space-y-6">
      {/* 标题编辑 */}
      <div className="group">
        <label className="flex items-center gap-2 text-sm font-bold mb-3" style={{ color: '#374151' }}>
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center text-white">
            <Type className="w-4 h-4" />
          </div>
          海报标题
        </label>
        <div className="relative">
          <input
            type="text"
            value={title}
            onChange={(e) => onTitleChange(e.target.value)}
            maxLength={50}
            className={`${inputBaseStyle} bg-white hover:border-gray-300 focus:border-blue-500 focus:shadow-md font-medium`}
            style={{ borderColor: '#E5E7EB' }}
            placeholder="例如：今日五行穿搭推荐"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium text-stone-500">
            {title.length}/50
          </div>
        </div>
      </div>

      {/* 推荐文案 */}
      <div className="group">
        <label className="flex items-center gap-2 text-sm font-bold mb-3" style={{ color: '#374151' }}>
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white">
            <MessageSquare className="w-4 h-4" />
          </div>
          推荐文案
        </label>
        <div className="relative">
          <textarea
            value={quote}
            onChange={(e) => onQuoteChange(e.target.value)}
            maxLength={200}
            rows={3}
            className={`${inputBaseStyle} bg-white hover:border-gray-300 focus:border-purple-500 focus:shadow-md resize-none font-medium`}
            style={{ borderColor: '#E5E7EB' }}
            placeholder="例如：火生土，今日事业运旺"
          />
          <div className="absolute right-3 bottom-3 text-xs font-medium text-stone-500">
            {quote.length}/200
          </div>
        </div>
      </div>

      {/* 个人签名 */}
      <div className="group">
        <label className="flex items-center gap-2 text-sm font-bold mb-3" style={{ color: '#374151' }}>
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center text-white">
            <PenTool className="w-4 h-4" />
          </div>
          个人签名
        </label>
        <div className="relative">
          <input
            type="text"
            value={signature}
            onChange={(e) => onSignatureChange(e.target.value)}
            maxLength={30}
            className={`${inputBaseStyle} bg-white hover:border-gray-300 focus:border-amber-500 focus:shadow-md font-medium`}
            style={{ borderColor: '#E5E7EB' }}
            placeholder="例如：顺衣尚"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium text-stone-500">
            {signature.length}/30
          </div>
        </div>
      </div>

      {/* 配色主题 */}
      <div className="group">
        <label className="flex items-center gap-2 text-sm font-bold mb-4" style={{ color: '#374151' }}>
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center text-white">
            <Palette className="w-4 h-4" />
          </div>
          配色主题
        </label>
        <div className="grid grid-cols-5 gap-3" role="radiogroup" aria-label="五行配色主题">
          {Object.entries(WUXING_THEMES).map(([key, t]) => {
            const isSelected = theme.name === t.name;
            return (
              <button
                key={key}
                onClick={() => onThemeChange(t)}
                className={`relative group/theme p-3 rounded-xl border-2 transition-all duration-300 min-h-[72px] focus:outline-none focus:ring-2 focus:ring-purple-500 ${
                  isSelected
                    ? 'border-white shadow-lg scale-105'
                    : 'border-transparent hover:border-white/50 hover:shadow-md'
                }`}
                role="radio"
                aria-checked={isSelected}
                aria-label={`${t.name}主题`}
                title={t.name}
              >
                {/* 选中指示器 */}
                {isSelected && (
                  <div className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-gradient-to-r from-green-400 to-emerald-500 flex items-center justify-center text-white text-xs font-bold shadow-md z-10" aria-hidden="true">
                    ✓
                  </div>
                )}

                {/* 颜色预览 */}
                <div
                  className="w-full h-12 rounded-lg mb-2 shadow-sm group-hover/theme:scale-110 transition-transform duration-300"
                  style={{ 
                    background: `linear-gradient(135deg, ${t.primary}, ${t.secondary})`,
                    boxShadow: `0 4px 12px ${t.primary}40`,
                  }}
                  aria-hidden="true"
                />
                
                {/* 名称 */}
                <p className="text-xs text-center font-bold" style={{ color: '#374151' }}>
                  {t.name}
                </p>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
