/**
 * 海报生成 API 客户端
 * 调用后端 Pillow 服务生成高质量海报
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface PosterGenerateParams {
  layout: 'simple' | 'wuxing' | 'card';
  title: string;
  items: Array<{
    name: string;
    image_url?: string;
    primary_element?: string;
    color?: string;
  }>;
  xiyong_elements: string[];
  theme: string;
  quote?: string;
  signature?: string;
  scene?: string;
}

/**
 * 生成海报并下载（直接返回二进制流）
 */
export async function generateAndDownloadPoster(params: PosterGenerateParams): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/api/poster/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      throw new Error(`海报生成失败: ${response.statusText}`);
    }

    // 获取 Blob
    const blob = await response.blob();
    
    // 创建下载链接
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${params.title}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error('海报下载失败:', error);
    throw error;
  }
}

/**
 * 生成海报并返回 Base64（用于分享）
 */
export async function generatePosterBase64(params: PosterGenerateParams): Promise<{
  image: string;
  filename: string;
  size: number;
}> {
  try {
    const response = await fetch(`${API_BASE}/api/poster/generate-base64`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      throw new Error(`海报生成失败: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('海报生成失败:', error);
    throw error;
  }
}

/**
 * Base64 转 Blob
 */
export function base64ToBlob(base64: string, mimeType: string = 'image/png'): Blob {
  const byteCharacters = atob(base64);
  const byteArrays = [];

  for (let offset = 0; offset < byteCharacters.length; offset += 512) {
    const slice = byteCharacters.slice(offset, offset + 512);
    const byteNumbers = new Array(slice.length);
    
    for (let i = 0; i < slice.length; i++) {
      byteNumbers[i] = slice.charCodeAt(i);
    }
    
    const byteArray = new Uint8Array(byteNumbers);
    byteArrays.push(byteArray);
  }

  return new Blob(byteArrays, { type: mimeType });
}

/**
 * 分享海报（使用 Base64）
 */
export async function sharePosterWithBase64(params: PosterGenerateParams): Promise<void> {
  try {
    // 生成 Base64 海报
    const { image, filename } = await generatePosterBase64(params);
    
    // 转换为 Blob
    const blob = base64ToBlob(image);
    
    // 尝试使用 Web Share API
    if (navigator.share && navigator.canShare) {
      const file = new File([blob], filename, { type: 'image/png' });
      const shareData = {
        title: params.title,
        text: params.quote || '来看看我的五行穿搭推荐吧！',
        files: [file],
      };

      if (navigator.canShare(shareData)) {
        await navigator.share(shareData);
        return;
      }
    }
    
    // 降级：下载
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error('分享失败:', error);
    throw error;
  }
}
