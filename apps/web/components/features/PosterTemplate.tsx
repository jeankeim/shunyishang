import React from 'react';
import { POSTER_TEMPLATES, ColorTheme } from '@/lib/poster-templates';
import { Sparkles, Stars, Smartphone, Landmark } from 'lucide-react';
import { getImageUrl } from '@/lib/image';

interface PosterTemplateItem {
  name: string;
  image_url?: string;
  primary_element?: string;
  color?: string;
  category?: string;
  reason?: string;
}

interface PosterTemplateProps {
  layout: 'simple' | 'wuxing' | 'card' | 'guofeng';
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
            我的个人衣橱
          </span>
        </div>
        <div className="text-right">
          <div className="text-xs opacity-50" style={{ color: '#9CA3AF' }}>
            {new Date().toLocaleDateString('zh-CN')}
          </div>
        </div>
      </div>

      {/* 底部引导文字 */}
      <div className="relative z-10 px-10 py-2 text-center" style={{ background: 'rgba(255,255,255,0.3)' }}>
        <p className="text-[10px] tracking-wider" style={{ color: '#9CA3AF' }}>
          扫码登录 shunyishang.com 体验更多功能
        </p>
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
            <div className="text-xs font-semibold tracking-wider">我的个人衣橱</div>
            <div className="text-xs opacity-50">传统智慧 · 现代穿搭</div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs opacity-60 mb-1">
            生成时间：{new Date().toLocaleTimeString('zh-CN', { hour12: false })}
          </div>
          <div className="text-sm font-semibold tracking-wider">—— 我的个人衣橱</div>
        </div>
      </div>

      {/* 底部引导文字 */}
      <div className="relative z-10 px-10 py-2 text-center" style={{ background: 'rgba(0,0,0,0.15)' }}>
        <p className="text-[10px] tracking-wider" style={{ color: 'rgba(255,255,255,0.4)' }}>
          扫码登录 shunyishang.com 体验更多功能
        </p>
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
        <div className="grid grid-cols-2 gap-4 mb-5">
          {items.slice(0, 4).map((item, index) => (
            <div
              key={index}
              className="group relative bg-white rounded-2xl overflow-hidden shadow-md"
              style={{
                border: '1px solid rgba(0, 0, 0, 0.06)',
              }}
            >
              {/* 图片 */}
              {item.image_url ? (
                <div className="relative w-full overflow-hidden" style={{ aspectRatio: '4/3' }}>
                  <img
                    src={getImageUrl(item.image_url)}
                    alt={item.name}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                  {/* 渐变遮罩 */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                  
                  {/* 序号标签 */}
                  <div className="absolute top-3 left-3 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold text-white" 
                       style={{ 
                         background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})`,
                         boxShadow: `0 2px 8px ${theme.primary}40`,
                       }}>
                    {index + 1}
                  </div>
                </div>
              ) : (
                <div className="w-full bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center" style={{ aspectRatio: '4/3' }}>
                  <span className="text-4xl opacity-30">👕</span>
                </div>
              )}
              
              {/* 信息 */}
              <div className="p-4">
                <p className="text-sm font-bold truncate mb-2">{item.name}</p>
                <div className="flex items-center gap-2">
                  {item.primary_element && (
                    <span className="inline-block px-2.5 py-1 rounded-full text-xs font-medium" 
                          style={{ 
                            background: `${theme.primary}15`,
                            color: theme.primary,
                          }}>
                      {item.primary_element}
                    </span>
                  )}
                  {item.color && (
                    <span className="inline-block px-2.5 py-1 rounded-full text-xs" 
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

        {/* 互动数据（海报分享用 - 展示五行标签和推荐信息） */}
        <div className="p-5 rounded-2xl mb-4" style={{
          background: 'rgba(255, 255, 255, 0.8)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(0, 0, 0, 0.06)',
        }}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-5">
              <div className="flex items-center gap-2 text-base text-gray-600">
                <span className="text-xl">👗</span>
                <span className="font-semibold">{items.length}件单品</span>
              </div>
              {scene && (
                <div className="flex items-center gap-2 text-base text-gray-600">
                  <span className="text-xl">🎯</span>
                  <span className="font-semibold">{scene}</span>
                </div>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-sm text-gray-500">
              <span>✨</span>
              <span>AI推荐</span>
            </div>
          </div>
          
          {/* 标签 */}
          <div className="flex flex-wrap gap-2.5">
            {xiyongElements?.map((element) => (
              <span
                key={element}
                className="px-4 py-1.5 rounded-full text-sm font-bold" 
                style={{ 
                  background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})`,
                  color: 'white',
                  boxShadow: `0 2px 8px ${theme.primary}30`,
                }}
              >
                #{element}穿搭
              </span>
            ))}
            <span className="px-4 py-1.5 rounded-full text-sm" style={{ 
              background: 'rgba(0,0,0,0.05)',
            }}>
              #AI推荐
            </span>
          </div>
        </div>

        {/* 签名 */}
        {signature && (
          <div className="text-center py-3">
            <p className="text-base italic opacity-60">—— {signature}</p>
          </div>
        )}
      </div>

      {/* 底部品牌标识 */}
      <div className="relative z-10 px-8 py-4 flex items-center justify-between" style={{ 
        borderTop: '1px solid rgba(0,0,0,0.08)',
        background: 'rgba(255,255,255,0.7)',
        backdropFilter: 'blur(10px)',
      }}>
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded" style={{ 
            background: `linear-gradient(135deg, ${theme.primary}, ${theme.secondary})` 
          }} />
          <span className="text-sm font-bold tracking-wider opacity-80">
            我的个人衣橱
          </span>
        </div>
        <div className="text-right">
          <div className="text-sm opacity-60">
            {new Date().toLocaleDateString('zh-CN')}
          </div>
        </div>
      </div>

      {/* 底部引导文字 */}
      <div className="relative z-10 px-8 py-3 text-center" style={{ background: 'rgba(255,255,255,0.5)' }}>
        <p className="text-sm tracking-wider" style={{ color: '#9CA3AF' }}>
          扫码登录 shunyishang.com 体验更多功能
        </p>
      </div>
    </div>
  );
};

// 主模板组件
// 宋锦国风模板 - 宣纸水墨 · 印章回纹 · 整套搭配展示
const GUOFENG_ELEMENT_COLORS: Record<string, string> = {
  '木': '#4E8560', '火': '#A85D57', '土': '#9C8654', '金': '#8FA3AB', '水': '#3F6C8E',
};
const GUOFENG_MAIN_PRIORITY = ['外套', '连衣裙', '裙装', '上装'];

const GuofengTemplate: React.FC<PosterTemplateProps> = ({
  title,
  items,
  xiyongElements = [],
  quote,
  theme,
  username,
}) => {
  const PAPER = '#F6F3E9', INK = '#2B2B2B', GRAY = '#7A7468', GOLD = '#B08D57', SEAL = '#A63D2F';
  const visible = items.slice(0, 6);
  let mainIdx = 0;
  for (const cat of GUOFENG_MAIN_PRIORITY) {
    const i = visible.findIndex(it => it.category === cat);
    if (i >= 0) { mainIdx = i; break; }
  }
  const hero = visible[mainIdx];
  const rest = visible.filter((_, i) => i !== mainIdx);
  const activeElements = new Set([...xiyongElements, ...visible.map(it => it.primary_element).filter(Boolean) as string[]]);
  const accent = GUOFENG_ELEMENT_COLORS[xiyongElements[0]] || theme.primary;

  return (
    <div
      className="w-full h-full flex flex-col relative overflow-hidden"
      style={{ background: PAPER, color: INK, fontFamily: '"Noto Serif SC", "Source Han Serif SC", "STSong", serif' }}
    >
      {/* 水墨晕染装饰 */}
      <div className="absolute -top-20 -left-24 w-72 h-72 rounded-full opacity-20 blur-3xl pointer-events-none" style={{ background: accent }} />
      <div className="absolute -top-16 -right-20 w-60 h-60 rounded-full opacity-15 blur-3xl pointer-events-none" style={{ background: accent }} />
      <div className="absolute -bottom-24 -left-20 w-64 h-64 rounded-full opacity-10 blur-3xl pointer-events-none" style={{ background: accent }} />

      {/* 顶部回纹装饰带 */}
      <div className="relative z-10 mx-8 mt-4 h-4" style={{
        backgroundImage: `repeating-linear-gradient(90deg, ${GOLD} 0px, ${GOLD} 2px, transparent 2px, transparent 6px)`,
        borderTop: `2px solid ${GOLD}`, borderBottom: `1px solid ${GOLD}55`, opacity: 0.7,
      }} />

      <div className="relative z-10 flex-1 px-8 py-4 flex flex-col">
        {/* 印章 + 标题 */}
        <div className="relative text-center mb-3">
          <div className="absolute left-0 top-0 w-12 h-12 rounded flex items-center justify-center text-white text-2xl font-bold shadow"
               style={{ background: SEAL }}>
            {xiyongElements[0] || '衣'}
          </div>
          <h1 className="text-3xl font-bold tracking-widest pt-2" style={{ color: INK }}>{title}</h1>
          <div className="mt-2 flex items-center justify-center gap-3">
            <div className="h-px w-24" style={{ background: GOLD }} />
            <div className="w-2 h-2 rotate-45" style={{ background: accent }} />
            <div className="h-px w-24" style={{ background: GOLD }} />
          </div>
          <p className="mt-2 text-sm tracking-[0.3em]" style={{ color: accent }}>五行相生 · 顺势而衣</p>
          <p className="mt-1 text-xs tracking-widest" style={{ color: GOLD }}>
            {username ? `· ${username} 的今日衣单 ·` : '· 今日衣单 ·'}
          </p>
        </div>

        {/* 搭配哲理引言 */}
        {quote && visible.length <= 4 && (
          <div className="mb-3 px-4 py-2 text-center text-xs leading-relaxed"
               style={{ color: '#4A4438', borderLeft: `2px solid ${GOLD}`, borderRight: `2px solid ${GOLD}` }}>
            {quote.length > 60 ? quote.slice(0, 60) + '…' : quote}
          </div>
        )}

        {/* 主件大视觉 */}
        {hero && (
          <div className="flex gap-4 mb-3">
            <div className="flex-shrink-0 w-32 h-32 p-1 rounded-lg" style={{ border: `2px solid ${GOLD}` }}>
              <div className="w-full h-full rounded overflow-hidden" style={{ border: `1px solid ${accent}` }}>
                {hero.image_url ? (
                  <img src={getImageUrl(hero.image_url)} alt={hero.name} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-2xl" style={{ background: '#EFEAD9' }}>衣</div>
                )}
              </div>
            </div>
            <div className="flex-1 min-w-0 py-1">
              <h3 className="text-base font-bold leading-snug line-clamp-2" style={{ color: INK }}>{hero.name}</h3>
              <div className="flex items-center gap-2 mt-1.5">
                {hero.primary_element && (
                  <span className="w-6 h-6 rounded-sm flex items-center justify-center text-white text-xs" style={{ background: SEAL }}>
                    {hero.primary_element}
                  </span>
                )}
                {hero.category && (
                  <span className="px-2 py-0.5 rounded text-xs" style={{ border: `1px solid ${GOLD}`, color: GRAY }}>
                    {hero.category}
                  </span>
                )}
              </div>
              {hero.reason && (
                <p className="mt-1.5 text-xs leading-relaxed line-clamp-3" style={{ color: GRAY }}>{hero.reason}</p>
              )}
            </div>
          </div>
        )}

        {/* 其余单品清单 */}
        <div className="space-y-2 flex-1">
          {rest.slice(0, 5).map((item, idx) => (
            <div key={idx} className="flex items-center gap-3 px-3 py-2 rounded-lg"
                 style={{ background: '#FFFDF6', border: `1px solid ${GOLD}66` }}>
              <div className="flex-shrink-0 w-12 h-12 rounded overflow-hidden">
                {item.image_url ? (
                  <img src={getImageUrl(item.image_url)} alt={item.name} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-sm" style={{ background: '#EFEAD9' }}>衣</div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold truncate" style={{ color: INK }}>{item.name}</p>
                <p className="text-xs truncate mt-0.5" style={{ color: GRAY }}>
                  {[item.category, item.reason].filter(Boolean).join(' · ')}
                </p>
              </div>
              {item.primary_element && (
                <span className="flex-shrink-0 w-6 h-6 rounded-sm flex items-center justify-center text-white text-xs" style={{ background: SEAL }}>
                  {item.primary_element}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* 五行相生环带 */}
        <div className="py-2 text-center">
          <p className="text-xs mb-1.5 tracking-widest" style={{ color: GOLD }}>五行相生 · 生生不息</p>
          <div className="flex items-center justify-center gap-1">
            {['木', '火', '土', '金', '水'].map((el, i) => (
              <React.Fragment key={el}>
                {i > 0 && <span className="text-[10px] px-0.5" style={{ color: '#B5AEA0' }}>生</span>}
                <span className="w-7 h-7 rounded-full flex items-center justify-center text-xs text-white"
                      style={activeElements.has(el)
                        ? { background: GUOFENG_ELEMENT_COLORS[el] }
                        : { border: '1px solid #C9C2B4', color: '#B5AEA0' }}>
                  {el}
                </span>
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* 底部品牌区 */}
        <div className="pt-2" style={{ borderTop: `1px solid ${GOLD}55` }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-sm flex items-center justify-center text-white text-xs" style={{ background: SEAL }}>顺</span>
              <span className="text-sm font-bold" style={{ color: INK }}>顺衣尚 · 五行穿搭</span>
            </div>
            <span className="text-xs" style={{ color: GRAY }}>传统智慧 · 现代穿搭</span>
          </div>
          <p className="mt-1 text-center text-[10px]" style={{ color: GRAY }}>扫码登录 shunyishang.com 领取专属五行穿搭</p>
        </div>
      </div>
    </div>
  );
};

export const PosterTemplate: React.FC<PosterTemplateProps> = (props) => {
  const { layout } = props;

  switch (layout) {
    case 'simple':
      return <SimpleTemplate {...props} />;
    case 'wuxing':
      return <WuxingTemplate {...props} />;
    case 'card':
      return <CardTemplate {...props} />;
    case 'guofeng':
      return <GuofengTemplate {...props} />;
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
      id: 'guofeng',
      name: '宋锦国风',
      desc: '宣纸水墨，整套搭配，五行相生',
      icon: Landmark,
      gradient: 'from-emerald-50 to-amber-50',
      border: 'border-emerald-300',
    },
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
