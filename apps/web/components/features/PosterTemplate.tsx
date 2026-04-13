import React from 'react';
import { POSTER_TEMPLATES, ColorTheme } from '@/lib/poster-templates';
import { Sparkles, Stars, Smartphone } from 'lucide-react';

interface PosterTemplateItem {
  name: string;
  image_url?: string;
  primary_element?: string;
  color?: string;
}

interface PosterTemplateProps {
  layout: 'simple' | 'wuxing' | 'card';
  title: string;
  items: PosterTemplateItem[];
  xiyongElements?: string[];
  scene?: string;
  quote?: string;
  signature?: string;
  theme: ColorTheme;
  username?: string;
}

// 简约风格模板 - 现代东方美学
const SimpleTemplate: React.FC<PosterTemplateProps> = ({
  title,
  items,
  xiyongElements,
  scene,
  quote,
  signature,
  theme,
}) => {
  // URL 转换函数：将相对路径转换为完整 URL
  const getImageUrl = (url: string | undefined): string | undefined => {
    if (!url) return undefined
    
    // 如果已经是完整 URL（http/https），直接返回
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url
    }
    
    // 公共库图片（/images/seed/...）使用 R2 存储
    if (url.startsWith('/images/')) {
      const R2_BASE = 'https://pub-886048e02a0443e2b0a3b749d8c30f46.r2.dev'
      return `${R2_BASE}${url}`
    }
    
    // 用户上传的图片（/uploads/...）使用后端 API
    if (url.startsWith('/uploads/')) {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      return `${API_BASE}${encodeURI(url)}`
    }
    
    // 其他相对路径使用后端 API
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    return `${API_BASE}${url}`
  }

  return (
    <div
      className="w-full h-full flex flex-col relative overflow-hidden"
      style={{
        background: '#FAFAF8',
        color: '#1A1A1A',
        fontFamily: '"Noto Serif SC", "Source Han Serif SC", "STSong", serif',
      }}
    >
      {/* 背景装饰纹理 */}
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
      }} />
      
      {/* 顶部装饰线 */}
      <div className="relative z-10">
        <div className="h-1.5 w-full" style={{ 
          background: `linear-gradient(90deg, ${theme.primary} 0%, ${theme.secondary} 100%)` 
        }} />
      </div>

      {/* 内容区 */}
      <div className="relative z-10 flex-1 px-10 py-8 flex flex-col">
        {/* 标题区 */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-3 tracking-wide" style={{ color: '#1A1A1A' }}>
            {title}
          </h1>
          {quote && (
            <p className="text-base italic opacity-70 leading-relaxed" style={{ color: '#4A4A4A' }}>
              "{quote}"
            </p>
          )}
          {/* 装饰分隔线 */}
          <div className="mt-4 flex items-center justify-center gap-3">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-gray-300" />
            <div className="w-2 h-2 rotate-45" style={{ backgroundColor: theme.primary }} />
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-gray-300" />
          </div>
        </div>

        {/* 穿搭列表 */}
        <div className="flex-1 space-y-4">
          {items.map((item, index) => (
            <div
              key={index}
              className="group flex items-start p-5 rounded-xl transition-all duration-300 hover:shadow-lg"
              style={{ 
                background: 'rgba(255, 255, 255, 0.8)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(0, 0, 0, 0.06)',
              }}
            >
              {/* 序号 */}
              <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold mr-4" 
                   style={{ 
                     background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})`,
                     color: 'white',
                   }}>
                {index + 1}
              </div>

              {/* 图片 */}
              {item.image_url && (
                <div className="flex-shrink-0 mr-5">
                  <div className="w-20 h-20 rounded-lg overflow-hidden shadow-md" style={{
                    border: '2px solid rgba(0,0,0,0.08)'
                  }}>
                    <img
                      src={getImageUrl(item.image_url)}
                      alt={item.name}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                      crossOrigin="anonymous"
                    />
                  </div>
                </div>
              )}

              {/* 信息 */}
              <div className="flex-1 min-w-0">
                <h3 className="font-bold text-lg mb-2 leading-tight" style={{ color: '#1A1A1A' }}>
                  {item.name}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {item.color && (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium" 
                          style={{ 
                            background: `${theme.primary}15`,
                            color: theme.primary,
                            border: `1px solid ${theme.primary}30`,
                          }}>
                      <span className="w-2 h-2 rounded-full mr-1.5" style={{ backgroundColor: item.color }} />
                      {item.color}
                    </span>
                  )}
                  {item.primary_element && (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium" 
                          style={{ 
                            background: `${theme.secondary}15`,
                            color: theme.secondary,
                            border: `1px solid ${theme.secondary}30`,
                          }}>
                      {item.primary_element}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 底部信息 */}
        <div className="mt-6 pt-6" style={{ borderTop: '1px solid rgba(0,0,0,0.08)' }}>
          <div className="grid grid-cols-2 gap-4 mb-4">
            {xiyongElements && xiyongElements.length > 0 && (
              <div className="flex items-center gap-2 whitespace-nowrap">
                <span className="text-sm font-semibold flex-shrink-0" style={{ color: '#6B7280' }}>喜用神</span>
                <div className="flex gap-1.5 flex-wrap">
                  {xiyongElements.map((el) => (
                    <span key={el} className="px-2.5 py-1 rounded text-xs font-bold flex-shrink-0" 
                          style={{ 
                            background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})`,
                            color: 'white',
                          }}>
                      {el}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {scene && (
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold" style={{ color: '#6B7280' }}>场景</span>
                <span className="text-sm" style={{ color: '#1A1A1A' }}>{scene}</span>
              </div>
            )}
          </div>
          
          {signature && (
            <div className="text-right mt-4">
              <p className="text-sm italic opacity-70" style={{ color: '#4A4A4A' }}>
                —— {signature}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 品牌标识 */}
      <div className="relative z-10 px-10 py-4 flex items-center justify-between" style={{ 
        borderTop: '1px solid rgba(0,0,0,0.06)',
        background: 'rgba(255,255,255,0.5)',
      }}>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded" style={{ 
            background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})` 
          }} />
          <span className="text-xs font-semibold tracking-wider" style={{ color: '#6B7280' }}>
            顺衣尚
          </span>
        </div>
        <div className="text-right">
          <div className="text-xs opacity-50" style={{ color: '#9CA3AF' }}>
            {new Date().toLocaleDateString('zh-CN')}
          </div>
        </div>
      </div>
    </div>
  );
};

// 五行风格模板 - 传统中国风
const WuxingTemplate: React.FC<PosterTemplateProps> = ({
  title,
  items,
  xiyongElements,
  scene,
  signature,
  theme,
}) => {
  // URL 转换函数：将相对路径转换为完整 URL
  const getImageUrl = (url: string | undefined): string | undefined => {
    if (!url) return undefined
    
    // 如果已经是完整 URL（http/https），直接返回
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url
    }
    
    // 公共库图片（/images/seed/...）使用 R2 存储
    if (url.startsWith('/images/')) {
      const R2_BASE = 'https://pub-886048e02a0443e2b0a3b749d8c30f46.r2.dev'
      return `${R2_BASE}${url}`
    }
    
    // 用户上传的图片（/uploads/...）使用后端 API
    if (url.startsWith('/uploads/')) {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      return `${API_BASE}${encodeURI(url)}`
    }
    
    // 其他相对路径使用后端 API
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    return `${API_BASE}${url}`
  }

  return (
    <div
      className="w-full h-full flex flex-col relative overflow-hidden"
      style={{
        background: `linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)`,
        color: '#FFFFFF',
        fontFamily: '"STKaiti", "KaiTi", "楷体", "Noto Serif SC", serif',
      }}
    >
      {/* 背景装饰 */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-10 left-10 w-32 h-32 rounded-full" style={{
          background: `radial-gradient(circle, ${theme.primary}40, transparent 70%)`,
          filter: 'blur(40px)',
        }} />
        <div className="absolute bottom-20 right-10 w-40 h-40 rounded-full" style={{
          background: `radial-gradient(circle, ${theme.secondary}40, transparent 70%)`,
          filter: 'blur(50px)',
        }} />
      </div>

      {/* 纹理叠加 */}
      <div className="absolute inset-0 opacity-[0.02]" style={{
        backgroundImage: `url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43-7c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM12 86c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm28-65c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm23-11c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-6 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm29 22c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zM32 63c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm57-13c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-9-21c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM60 91c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM35 41c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM12 60c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2z' fill='%23ffffff' fill-opacity='1' fill-rule='evenodd'/%3E%3C/svg%3E")`,
      }} />

      {/* 内容区 */}
      <div className="relative z-10 flex-1 px-10 py-8 flex flex-col">
        {/* 顶部五行图标 */}
        <div className="flex justify-center mb-6">
          <div className="relative">
            {/* 外圈装饰 */}
            <div className="absolute inset-0 rounded-full animate-pulse" style={{
              background: `radial-gradient(circle, ${theme.primary}30, transparent 70%)`,
              filter: 'blur(20px)',
            }} />
            <div
              className="relative w-24 h-24 rounded-full flex items-center justify-center text-4xl font-bold border-4 shadow-2xl"
              style={{ 
                borderColor: theme.primary,
                background: `linear-gradient(135deg, ${theme.primary}20, ${theme.secondary}20)`,
                boxShadow: `0 0 40px ${theme.primary}40, inset 0 0 20px ${theme.primary}20`,
              }}
            >
              {xiyongElements?.[0] || '五行'}
            </div>
          </div>
        </div>

        {/* 标题 */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-3 tracking-widest" style={{ 
            textShadow: `0 0 30px ${theme.primary}60`,
          }}>
            {title}
          </h1>
          <div className="flex items-center justify-center gap-3 mb-3">
            <div className="h-px w-16 bg-gradient-to-r from-transparent to-white/40" />
            <div className="w-1.5 h-1.5 rotate-45" style={{ backgroundColor: theme.primary }} />
            <div className="h-px w-16 bg-gradient-to-l from-transparent to-white/40" />
          </div>
          <p className="text-base opacity-80 tracking-wider">五行相生 · 运势亨通</p>
        </div>

        {/* 穿搭列表 */}
        <div className="flex-1 space-y-4">
          {items.map((item, index) => (
            <div
              key={index}
              className="group relative p-5 rounded-xl transition-all duration-300 hover:shadow-2xl"
              style={{ 
                background: 'rgba(255, 255, 255, 0.08)',
                backdropFilter: 'blur(20px)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
              }}
            >
              <div className="flex items-start gap-4">
                {/* 序号 */}
                <div className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold" 
                     style={{ 
                       background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})`,
                       boxShadow: `0 4px 15px ${theme.primary}40`,
                     }}>
                  {index + 1}
                </div>

                {/* 图片 */}
                {item.image_url && (
                  <div className="flex-shrink-0">
                    <div className="w-20 h-20 rounded-lg overflow-hidden shadow-lg" style={{
                      border: '2px solid rgba(255,255,255,0.2)',
                    }}>
                      <img
                        src={getImageUrl(item.image_url)}
                        alt={item.name}
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                        crossOrigin="anonymous"
                      />
                    </div>
                  </div>
                )}

                {/* 信息 */}
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-lg mb-2 leading-tight">
                    {item.name}
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {item.color && (
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium" 
                            style={{ 
                              background: `${theme.primary}30`,
                              border: `1px solid ${theme.primary}50`,
                            }}>
                        <span className="w-2 h-2 rounded-full mr-1.5" style={{ backgroundColor: item.color }} />
                        {item.color}
                      </span>
                    )}
                    {item.primary_element && (
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium" 
                            style={{ 
                              background: `${theme.secondary}30`,
                              border: `1px solid ${theme.secondary}50`,
                            }}>
                        {item.primary_element}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 底部信息 */}
        <div className="mt-6 pt-6" style={{ borderTop: '1px solid rgba(255,255,255,0.15)' }}>
          {scene && (
            <div className="text-center mb-4">
              <p className="text-lg tracking-wider">
                <span className="opacity-70">适宜：</span>
                <span className="font-semibold">{scene}</span>
              </p>
            </div>
          )}
          {signature && (
            <div className="text-center">
              <p className="text-sm opacity-70 italic">
                —— {signature}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 底部品牌区 */}
      <div className="relative z-10 px-10 py-6 flex items-center justify-between" style={{ 
        borderTop: '1px solid rgba(255,255,255,0.1)',
        background: 'rgba(0,0,0,0.2)',
      }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold" 
               style={{ 
                 background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})`,
                 boxShadow: `0 0 20px ${theme.primary}40`,
               }}>
            五行
          </div>
          <div>
            <div className="text-xs font-semibold tracking-wider">顺衣尚</div>
            <div className="text-xs opacity-50">传统智慧 · 现代穿搭</div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs opacity-60 mb-1">
            生成时间：{new Date().toLocaleTimeString('zh-CN', { hour12: false })}
          </div>
          <div className="text-sm font-semibold tracking-wider">—— 顺衣尚</div>
        </div>
      </div>
    </div>
  );
};

// 卡片风格模板 - 现代社交媒体风
const CardTemplate: React.FC<PosterTemplateProps> = ({
  title,
  items,
  xiyongElements,
  scene,
  signature,
  theme,
  username,
}) => {
  // URL 转换函数：将相对路径转换为完整 URL
  const getImageUrl = (url: string | undefined): string | undefined => {
    if (!url) return undefined
    
    // 如果已经是完整 URL（http/https），直接返回
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url
    }
    
    // 公共库图片（/images/seed/...）使用 R2 存储
    if (url.startsWith('/images/')) {
      const R2_BASE = 'https://pub-886048e02a0443e2b0a3b749d8c30f46.r2.dev'
      return `${R2_BASE}${url}`
    }
    
    // 用户上传的图片（/uploads/...）使用后端 API
    if (url.startsWith('/uploads/')) {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      return `${API_BASE}${encodeURI(url)}`
    }
    
    // 其他相对路径使用后端 API
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    return `${API_BASE}${url}`
  }

  return (
    <div
      className="w-full h-full flex flex-col relative overflow-hidden"
      style={{
        background: 'linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%)',
        color: '#212529',
        fontFamily: '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
      }}
    >
      {/* 背景装饰 */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute top-0 right-0 w-64 h-64 rounded-full" style={{
          background: `radial-gradient(circle, ${theme.primary}20, transparent 70%)`,
          filter: 'blur(60px)',
        }} />
        <div className="absolute bottom-0 left-0 w-64 h-64 rounded-full" style={{
          background: `radial-gradient(circle, ${theme.secondary}20, transparent 70%)`,
          filter: 'blur(60px)',
        }} />
      </div>

      {/* 内容区 */}
      <div className="relative z-10 flex-1 px-8 py-6 flex flex-col">
        {/* 用户信息头部 */}
        <div className="flex items-center justify-between mb-6 p-4 rounded-2xl" style={{
          background: 'rgba(255, 255, 255, 0.8)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(0, 0, 0, 0.06)',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.05)',
        }}>
          <div className="flex items-center gap-3">
            {/* 头像 */}
            <div className="relative">
              <div className="w-14 h-14 rounded-full flex items-center justify-center text-2xl font-bold text-white" 
                   style={{ 
                     background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})`,
                     boxShadow: `0 4px 15px ${theme.primary}40`,
                   }}>
                {username?.[0] || 'U'}
              </div>
              {/* 在线状态点 */}
              <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-green-500 rounded-full border-2 border-white" />
            </div>
            <div>
              <h3 className="font-bold text-base">@{username || '用户'}</h3>
              <p className="text-xs opacity-60">刚刚发布 · 五行穿搭</p>
            </div>
          </div>
          {/* 更多操作按钮 */}
          <button className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-gray-100 transition-colors">
            <span className="text-lg">⋯</span>
          </button>
        </div>

        {/* 标题和文案 */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold mb-2 leading-tight">
            {title}
          </h1>
          {scene && (
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🎯</span>
              <p className="text-sm opacity-70">{scene}</p>
            </div>
          )}
        </div>

        {/* 单品网格 */}
        <div className="flex-1 grid grid-cols-2 gap-3 mb-4">
          {items.slice(0, 4).map((item, index) => (
            <div
              key={index}
              className="group relative bg-white rounded-2xl overflow-hidden shadow-md hover:shadow-xl transition-all duration-300 hover:-translate-y-1"
              style={{
                border: '1px solid rgba(0, 0, 0, 0.06)',
              }}
            >
              {/* 图片 */}
              {item.image_url ? (
                <div className="relative w-full h-28 overflow-hidden">
                  <img
                    src={getImageUrl(item.image_url)}
                    alt={item.name}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                    crossOrigin="anonymous"
                  />
                  {/* 渐变遮罩 */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                  
                  {/* 序号标签 */}
                  <div className="absolute top-2 left-2 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white" 
                       style={{ 
                         background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})`,
                         boxShadow: `0 2px 8px ${theme.primary}40`,
                       }}>
                    {index + 1}
                  </div>
                </div>
              ) : (
                <div className="w-full h-28 bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
                  <span className="text-3xl opacity-30">👕</span>
                </div>
              )}
              
              {/* 信息 */}
              <div className="p-3">
                <p className="text-xs font-bold truncate mb-1">{item.name}</p>
                <div className="flex items-center gap-1.5">
                  {item.primary_element && (
                    <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium" 
                          style={{ 
                            background: `${theme.primary}15`,
                            color: theme.primary,
                          }}>
                      {item.primary_element}
                    </span>
                  )}
                  {item.color && (
                    <span className="inline-block px-2 py-0.5 rounded-full text-xs" 
                          style={{ 
                            background: 'rgba(0,0,0,0.05)',
                            opacity: 0.7,
                          }}>
                      {item.color}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 互动数据 */}
        <div className="p-4 rounded-2xl mb-4" style={{
          background: 'rgba(255, 255, 255, 0.8)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(0, 0, 0, 0.06)',
        }}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-4">
              <button className="flex items-center gap-1.5 text-sm hover:text-red-500 transition-colors group">
                <span className="text-lg group-hover:scale-110 transition-transform">❤️</span>
                <span className="font-medium">128</span>
              </button>
              <button className="flex items-center gap-1.5 text-sm hover:text-blue-500 transition-colors">
                <span className="text-lg">💬</span>
                <span className="font-medium">32</span>
              </button>
              <button className="flex items-center gap-1.5 text-sm hover:text-green-500 transition-colors">
                <span className="text-lg">↗️</span>
                <span className="font-medium">分享</span>
              </button>
            </div>
            <button className="text-lg hover:scale-110 transition-transform">
              🔖
            </button>
          </div>
          
          {/* 标签 */}
          <div className="flex flex-wrap gap-2">
            {xiyongElements?.map((element) => (
              <span
                key={element}
                className="px-3 py-1 rounded-full text-xs font-bold" 
                style={{ 
                  background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})`,
                  color: 'white',
                  boxShadow: `0 2px 8px ${theme.primary}30`,
                }}
              >
                #{element}穿搭
              </span>
            ))}
            <span className="px-3 py-1 rounded-full text-xs" style={{ 
              background: 'rgba(0,0,0,0.05)',
            }}>
              #AI推荐
            </span>
          </div>
        </div>

        {/* 签名 */}
        {signature && (
          <div className="text-center py-2">
            <p className="text-sm italic opacity-60">—— {signature}</p>
          </div>
        )}
      </div>

      {/* 底部品牌标识 */}
      <div className="relative z-10 px-8 py-3 flex items-center justify-between" style={{ 
        borderTop: '1px solid rgba(0,0,0,0.06)',
        background: 'rgba(255,255,255,0.6)',
        backdropFilter: 'blur(10px)',
      }}>
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded" style={{ 
            background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})` 
          }} />
          <span className="text-xs font-bold tracking-wider opacity-70">
            顺衣尚
          </span>
        </div>
        <div className="text-right">
          <div className="text-xs opacity-50">
            {new Date().toLocaleDateString('zh-CN')}
          </div>
        </div>
      </div>
    </div>
  );
};

// 主模板组件
export const PosterTemplate: React.FC<PosterTemplateProps> = (props) => {
  const { layout } = props;

  switch (layout) {
    case 'simple':
      return <SimpleTemplate {...props} />;
    case 'wuxing':
      return <WuxingTemplate {...props} />;
    case 'card':
      return <CardTemplate {...props} />;
    default:
      return <SimpleTemplate {...props} />;
  }
};

// 模板选择器 - 优化版
export const PosterTemplateSelector: React.FC<{
  selectedTemplate: string;
  onSelect: (templateId: string) => void;
}> = ({ selectedTemplate, onSelect }) => {
  const templates = [
    { 
      id: 'simple', 
      name: '简约东方', 
      desc: '现代极简，突出单品',
      icon: Sparkles,
      gradient: 'from-amber-50 to-orange-50',
      border: 'border-amber-200',
    },
    { 
      id: 'wuxing', 
      name: '五行国潮', 
      desc: '传统美学，文化底蕴',
      icon: Stars,
      gradient: 'from-indigo-900 to-blue-900',
      border: 'border-indigo-700',
    },
    { 
      id: 'card', 
      name: '社交卡片', 
      desc: '时尚潮流，适合分享',
      icon: Smartphone,
      gradient: 'from-purple-50 to-pink-50',
      border: 'border-purple-200',
    },
  ];

  return (
    <div className="space-y-3">
      {templates.map((template) => {
        const isSelected = selectedTemplate === template.id;
        const IconComponent = template.icon;
        return (
          <button
            key={template.id}
            onClick={() => onSelect(template.id)}
            className={`relative w-full p-4 rounded-xl border-2 transition-all duration-300 text-left group hover:shadow-lg min-h-[88px] focus:outline-none focus:ring-2 focus:ring-purple-500 ${
              isSelected
                ? `${template.border} bg-white shadow-md scale-[1.02]`
                : 'border-gray-200 bg-white hover:border-gray-300'
            }`}
            aria-pressed={isSelected}
            aria-label={`选择${template.name}模板：${template.desc}`}
          >
            {/* 选中指示器 */}
            {isSelected && (
              <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-gradient-to-r from-green-400 to-emerald-500 flex items-center justify-center text-white text-xs font-bold shadow-md" aria-hidden="true">
                ✓
              </div>
            )}

            <div className="flex items-start gap-4">
              {/* 图标 */}
              <div className={`flex-shrink-0 w-14 h-14 rounded-xl bg-gradient-to-br ${template.gradient} flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform duration-300`}>
                <IconComponent className="w-7 h-7" aria-hidden="true" />
              </div>

              {/* 信息 */}
              <div className="flex-1 min-w-0">
                <h4 className="font-bold text-base mb-1" style={{ color: '#1A1A1A' }}>
                  {template.name}
                </h4>
                <p className="text-sm opacity-60 leading-relaxed">
                  {template.desc}
                </p>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
};
