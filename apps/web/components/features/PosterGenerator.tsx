import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PosterTemplate, PosterTemplateSelector } from './PosterTemplate';
import { PosterEditor } from './PosterEditor';
import { usePoster } from '@/hooks/usePoster';
import { POSTER_TEMPLATES } from '@/lib/poster-templates';
import { Download, Share2, Sparkles, X, Palette, Edit3 } from 'lucide-react';

interface PosterGeneratorProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  items: Array<{
    name: string;
    image_url?: string;
    primary_element?: string;
    color?: string;
  }>;
  xiyongElements?: string[];
  scene?: string;
  quote?: string;
  username?: string;
}

export const PosterGenerator: React.FC<PosterGeneratorProps> = ({
  isOpen,
  onClose,
  title: initialTitle,
  items,
  xiyongElements = [],
  scene = '',
  quote = '',
  username,
}) => {
  const [activeTab, setActiveTab] = useState<'template' | 'edit'>('template');
  
  const poster = usePoster({
    initialTitle: initialTitle || '今日五行穿搭推荐',
    initialQuote: quote,
    items,
    xiyongElements,
    scene,
    username,
  });

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="poster-dialog-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ type: "spring", duration: 0.5, bounce: 0.2 }}
        className="bg-white rounded-3xl shadow-2xl max-w-7xl w-full max-h-[92vh] overflow-hidden"
        style={{
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.05)',
        }}
      >
        {/* 头部 */}
        <div className="relative flex items-center justify-between px-8 py-6" style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}>
          {/* 背景装饰 */}
          <div className="absolute inset-0 overflow-hidden">
            <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-white/10 blur-2xl" />
            <div className="absolute -bottom-10 -left-10 w-40 h-40 rounded-full bg-white/10 blur-2xl" />
          </div>

          <div className="relative flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 id="poster-dialog-title" className="text-2xl font-bold text-white tracking-wide">生成分享海报</h2>
              <p className="text-sm text-white/80">选择模板，编辑内容，一键分享</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="relative w-12 h-12 rounded-xl bg-white/10 hover:bg-white/20 flex items-center justify-center transition-all duration-200 hover:scale-110 focus:outline-none focus:ring-2 focus:ring-white/50"
            aria-label="关闭海报生成器"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>

        <div className="flex h-[calc(92vh-120px)]">
          {/* 左侧：编辑区 */}
          <div className="w-[420px] border-r border-gray-200 flex flex-col bg-gradient-to-b from-gray-50 to-white">
            {/* Tab 切换 */}
            <div className="flex border-b border-gray-200 bg-white">
              <button
                onClick={() => setActiveTab('template')}
                className={`flex-1 flex items-center justify-center gap-2 py-4 text-sm font-bold transition-all duration-200 relative focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-inset ${
                  activeTab === 'template'
                    ? 'text-purple-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                role="tab"
                aria-selected={activeTab === 'template'}
                aria-controls="template-panel"
                id="template-tab"
              >
                <Palette className="w-4 h-4" aria-hidden="true" />
                选择模板
                {activeTab === 'template' && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute bottom-0 left-4 right-4 h-1 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
              </button>
              <button
                onClick={() => setActiveTab('edit')}
                className={`flex-1 flex items-center justify-center gap-2 py-4 text-sm font-bold transition-all duration-200 relative focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-inset ${
                  activeTab === 'edit'
                    ? 'text-purple-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                role="tab"
                aria-selected={activeTab === 'edit'}
                aria-controls="edit-panel"
                id="edit-tab"
              >
                <Edit3 className="w-4 h-4" aria-hidden="true" />
                编辑内容
                {activeTab === 'edit' && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute bottom-0 left-4 right-4 h-1 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
              </button>
            </div>

            {/* 内容区 */}
            <div className="flex-1 overflow-y-auto p-6" style={{ touchAction: 'manipulation' }}>
              <AnimatePresence mode="wait">
                {activeTab === 'template' ? (
                  <motion.div
                    key="template"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    transition={{ duration: 0.2 }}
                    role="tabpanel"
                    id="template-panel"
                    aria-labelledby="template-tab"
                  >
                    <PosterTemplateSelector
                      selectedTemplate={poster.selectedTemplate}
                      onSelect={poster.setSelectedTemplate}
                    />
                  </motion.div>
                ) : (
                  <motion.div
                    key="edit"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.2 }}
                    role="tabpanel"
                    id="edit-panel"
                    aria-labelledby="edit-tab"
                  >
                    <PosterEditor
                      title={poster.title}
                      onTitleChange={poster.setTitle}
                      quote={poster.quote}
                      onQuoteChange={poster.setQuote}
                      signature={poster.signature}
                      onSignatureChange={poster.setSignature}
                      theme={poster.selectedTheme}
                      onThemeChange={poster.setSelectedTheme}
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* 错误提示 */}
            {poster.error && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 mx-6 mb-4 bg-red-50 border border-red-200 rounded-xl"
              >
                <p className="text-sm text-red-600 font-medium">{poster.error}</p>
              </motion.div>
            )}

            {/* 操作按钮 */}
            <div className="p-6 border-t border-gray-200 bg-white space-y-3">
              <button
                onClick={poster.download}
                disabled={poster.isGenerating}
                className="w-full flex items-center justify-center gap-3 px-6 py-4 min-h-[52px] bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl font-bold text-base hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
                aria-label={poster.isGenerating ? '正在生成海报' : '下载高清海报'}
              >
                <Download className="w-5 h-5" aria-hidden="true" />
                {poster.isGenerating ? (
                  <span className="flex items-center gap-2">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                      className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                      aria-hidden="true"
                    />
                    生成中...
                  </span>
                ) : (
                  '下载高清海报'
                )}
              </button>
              <button
                onClick={poster.share}
                disabled={poster.isGenerating}
                className="w-full flex items-center justify-center gap-3 px-6 py-4 min-h-[52px] bg-white border-2 border-gray-200 text-gray-700 rounded-xl font-bold text-base hover:bg-gray-50 hover:border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2"
                aria-label="分享到社交平台"
              >
                <Share2 className="w-5 h-5" aria-hidden="true" />
                分享到社交平台
              </button>
            </div>
          </div>

          {/* 右侧：预览区 */}
          <div className="flex-1 bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center p-8 overflow-auto relative">
            {/* 背景装饰 */}
            <div className="absolute inset-0 overflow-hidden">
              <div className="absolute top-20 left-20 w-64 h-64 rounded-full bg-purple-200/30 blur-3xl" />
              <div className="absolute bottom-20 right-20 w-64 h-64 rounded-full bg-pink-200/30 blur-3xl" />
            </div>

            {/* 海报预览 */}
            <div className="relative">
              {/* 阴影效果 */}
              <div className="absolute inset-0 bg-black/20 blur-2xl rounded-2xl transform scale-[0.98] translate-y-4" />
              
              <div
                className="relative shadow-2xl rounded-2xl overflow-hidden"
                style={{
                  width: '540px',
                  height: '960px',
                  transform: 'scale(0.65)',
                  transformOrigin: 'center center',
                }}
              >
                <div ref={poster.posterRef} className="w-full h-full">
                  <PosterTemplate
                    layout={poster.selectedTemplate as 'simple' | 'wuxing' | 'card'}
                    title={poster.title}
                    items={poster.items}
                    xiyongElements={poster.xiyongElements}
                    scene={poster.scene}
                    quote={poster.quote}
                    signature={poster.signature}
                    theme={poster.selectedTheme}
                    username={username}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
