// @ts-ignore - dom-to-image-more 没有 TypeScript 类型定义
import domtoimage from 'dom-to-image-more';

// dom-to-image 配置 - 支持 oklab 颜色空间和跨域图片
export const DOM_TO_IMAGE_CONFIG = {
  quality: 1.0, // 最高质量
  bgcolor: '#FFFFFF', // 白色背景
  width: 540 * 2, // 2x 分辨率
  height: 960 * 2,
  cacheBust: true, // 防止缓存问题
  imagePlaceholder: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', // 1x1 透明占位图
  style: {
    transform: 'scale(2)',
    transformOrigin: 'top left',
  },
  // 过滤函数 - 确保图片元素被正确处理
  filter: (node: HTMLElement) => {
    // 确保所有图片都有 crossOrigin 属性
    if (node.tagName === 'IMG') {
      const img = node as HTMLImageElement;
      if (!img.hasAttribute('crossorigin')) {
        img.setAttribute('crossorigin', 'anonymous');
      }
    }
    return true;
  },
};

/**
 * 生成海报图片
 * @param element - 要捕获的 DOM 元素
 * @returns Promise<Blob> - 生成的图片 Blob
 */
export async function generatePosterImage(element: HTMLElement): Promise<Blob> {
  try {
    // 使用 dom-to-image-more，它支持 oklab 颜色空间
    const dataUrl = await domtoimage.toPng(element, DOM_TO_IMAGE_CONFIG);
    
    // 将 data URL 转换为 Blob
    const response = await fetch(dataUrl);
    const blob = await response.blob();
    
    return blob;
  } catch (error) {
    console.error('海报生成失败:', error);
    throw error;
  }
}

/**
 * 下载海报图片
 * @param blob - 图片 Blob
 * @param filename - 文件名
 */
export function downloadPoster(blob: Blob, filename: string = '五行穿搭海报.png'): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * 分享海报（移动端）
 * @param blob - 图片 Blob
 * @param title - 分享标题
 * @param text - 分享文本
 */
export async function sharePoster(
  blob: Blob,
  title: string = '我的五行穿搭推荐',
  text: string = '来看看我的五行穿搭推荐吧！'
): Promise<void> {
  // 检查是否支持 Web Share API
  if (navigator.share && navigator.canShare) {
    const file = new File([blob], 'poster.png', { type: 'image/png' });
    const filesArray = [file];
    
    const shareData = {
      title,
      text,
      files: filesArray,
    };

    if (navigator.canShare(shareData)) {
      try {
        await navigator.share(shareData);
      } catch (error) {
        // 用户取消分享或分享失败
        if ((error as Error).name !== 'AbortError') {
          console.error('分享失败:', error);
          throw error;
        }
      }
    } else {
      // 不支持文件分享，回退到下载
      downloadPoster(blob);
    }
  } else {
    // 不支持 Web Share API，回退到下载
    downloadPoster(blob);
  }
}

/**
 * 复制海报到剪贴板
 * @param blob - 图片 Blob
 */
export async function copyPosterToClipboard(blob: Blob): Promise<void> {
  try {
    await navigator.clipboard.write([
      new ClipboardItem({
        'image/png': blob,
      }),
    ]);
  } catch (error) {
    console.error('复制到剪贴板失败:', error);
    throw error;
  }
}
