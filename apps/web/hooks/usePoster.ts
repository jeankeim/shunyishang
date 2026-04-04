import { useState, useCallback, useRef } from 'react';
import { generateAndDownloadPoster, sharePosterWithBase64, PosterGenerateParams } from '@/lib/poster-api';
import { DEFAULT_TEMPLATE, DEFAULT_THEME, PosterTemplate, ColorTheme } from '@/lib/poster-templates';

interface PosterItem {
  name: string;
  image_url?: string;
  primary_element?: string;
  color?: string;
}

interface UsePosterOptions {
  initialTitle?: string;
  initialQuote?: string;
  initialSignature?: string;
  items?: PosterItem[];
  xiyongElements?: string[];
  scene?: string;
  username?: string;
}

export function usePoster(options: UsePosterOptions = {}) {
  const [title, setTitle] = useState(options.initialTitle || '今日五行穿搭推荐');
  const [quote, setQuote] = useState(options.initialQuote || '');
  const [signature, setSignature] = useState(options.initialSignature || '顺衣尚');
  const [selectedTemplate, setSelectedTemplate] = useState(DEFAULT_TEMPLATE.id);
  const [selectedTheme, setSelectedTheme] = useState<ColorTheme>(DEFAULT_THEME);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const posterRef = useRef<HTMLDivElement>(null);

  const items: PosterItem[] = options.items || [];
  const xiyongElements = options.xiyongElements || [];
  const scene = options.scene || '';

  // 下载海报
  const download = useCallback(async () => {
    try {
      setIsGenerating(true);
      setError(null);
      
      // 构建请求参数
      const params: PosterGenerateParams = {
        layout: selectedTemplate as 'simple' | 'wuxing' | 'card',
        title,
        items: items.map(item => ({
          name: item.name,
          image_url: item.image_url,
          primary_element: item.primary_element,
          color: item.color,
        })),
        xiyong_elements: xiyongElements,
        theme: selectedTheme.name.toLowerCase(), // fire/wood/earth/metal/water
        quote,
        signature,
        scene,
      };
      
      // 调用后端 API 生成并下载
      await generateAndDownloadPoster(params);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '海报下载失败';
      setError(errorMessage);
      console.error('下载失败:', err);
    } finally {
      setIsGenerating(false);
    }
  }, [selectedTemplate, title, items, xiyongElements, selectedTheme, quote, signature, scene]);

  // 分享海报
  const share = useCallback(async () => {
    try {
      setIsGenerating(true);
      setError(null);
      
      // 构建请求参数
      const params: PosterGenerateParams = {
        layout: selectedTemplate as 'simple' | 'wuxing' | 'card',
        title,
        items: items.map(item => ({
          name: item.name,
          image_url: item.image_url,
          primary_element: item.primary_element,
          color: item.color,
        })),
        xiyong_elements: xiyongElements,
        theme: selectedTheme.name.toLowerCase(), // fire/wood/earth/metal/water
        quote,
        signature,
        scene,
      };
      
      // 调用后端 API 生成并分享
      await sharePosterWithBase64(params);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '海报分享失败';
      setError(errorMessage);
      console.error('分享失败:', err);
    } finally {
      setIsGenerating(false);
    }
  }, [selectedTemplate, title, items, xiyongElements, selectedTheme, quote, signature, scene]);

  // 重置海报
  const reset = useCallback(() => {
    setTitle(options.initialTitle || '今日五行穿搭推荐');
    setQuote(options.initialQuote || '');
    setSignature(options.initialSignature || '顺衣尚');
    setSelectedTemplate(DEFAULT_TEMPLATE.id);
    setSelectedTheme(DEFAULT_THEME);
    setError(null);
  }, [options.initialTitle, options.initialQuote, options.initialSignature]);

  return {
    // 状态
    title,
    setTitle,
    quote,
    setQuote,
    signature,
    setSignature,
    selectedTemplate,
    setSelectedTemplate,
    selectedTheme,
    setSelectedTheme,
    isGenerating,
    error,
    posterRef,
    
    // 数据
    items,
    xiyongElements,
    scene,
    
    // 操作
    download,
    share,
    reset,
  };
}
