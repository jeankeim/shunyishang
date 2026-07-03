/**
 * 图片 URL 处理公共工具
 * 统一处理 R2 公共库图片和用户上传图片的 URL 转换
 */

/** R2 公共访问基础 URL（从环境变量读取，消除硬编码） */
const R2_BASE = process.env.NEXT_PUBLIC_R2_PUBLIC_URL || 'https://pub-886048e02a0443e2b0a3b749d8c30f46.r2.dev'

/** 后端 API 基础 URL（浏览器环境返回空字符串，通过 Next.js rewrites 代理） */
function getAPIBase(): string {
  return typeof window !== 'undefined' ? '' : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
}

/**
 * 将相对路径图片 URL 转换为完整可访问的 URL
 *
 * - 完整 URL (http/https): 直接返回
 * - /images/ 前缀: 拼接 R2 公共存储 URL
 * - /uploads/ 前缀: 拼接后端 API URL（encodeURI 处理特殊字符）
 * - 其他相对路径: 拼接后端 API URL
 */
export function getImageUrl(url: string | undefined | null): string | undefined {
  if (!url) return undefined

  // 已经是完整 URL
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }

  // 公共库图片（/images/seed/...）使用 R2 存储
  if (url.startsWith('/images/')) {
    return `${R2_BASE}${url}`
  }

  // 用户上传的图片（/uploads/...）通过 Next.js rewrite 代理到后端
  // 返回相对路径，浏览器请求同源 localhost:3000/uploads/...，由 Next.js 代理到后端
  // 彻底消除跨域 CORS 问题
  if (url.startsWith('/uploads/')) {
    // decodeURI 防止数据库中已编码的 URL 被双重编码
    try { return encodeURI(decodeURI(url)) } catch { return encodeURI(url) }
  }

  // 其他相对路径使用后端 API
  return `${getAPIBase()}${url}`
}
