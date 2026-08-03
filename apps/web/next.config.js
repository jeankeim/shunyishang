/** @type {import('next').NextConfig} */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const R2_BASE = process.env.NEXT_PUBLIC_R2_PUBLIC_URL || 'https://pub-886048e02a0443e2b0a3b749d8c30f46.r2.dev'
const OSS_BASE = process.env.NEXT_PUBLIC_OSS_IMAGES_URL || ''
const IS_STATIC_EXPORT = process.env.NEXT_PUBLIC_STATIC_EXPORT === 'true'

// 从 URL 提取 hostname
function extractHostname(url, fallback) {
  try {
    return new URL(url).hostname
  } catch {
    return fallback
  }
}

const r2Hostname = extractHostname(R2_BASE, 'pub-886048e02a0443e2b0a3b749d8c30f46.r2.dev')
const apiHostname = extractHostname(API_BASE, 'localhost')
const ossHostname = extractHostname(OSS_BASE, '')

// 图片远程域名配置
const remotePatterns = [
  // R2（海外，兼容旧数据）
  { protocol: 'https', hostname: r2Hostname },
  // R2 当前实际公开域名
  { protocol: 'https', hostname: 'pub-851399ad134d447ea68cd62dbadd90a4.r2.dev' },
  // API 服务器（本地开发）
  {
    protocol: process.env.NODE_ENV === 'production' ? 'https' : 'http',
    hostname: apiHostname,
    port: process.env.NODE_ENV === 'production' ? '' : '8000',
  },
  // 占位图
  { protocol: 'https', hostname: 'placehold.co' },
]

// 如果配置了 OSS 图片域名，加入允许列表
if (ossHostname) {
  remotePatterns.push({ protocol: 'https', hostname: ossHostname })
}

// 基础配置
const nextConfig = {
  // Docker/Zeabur 部署使用 standalone 输出
  output: IS_STATIC_EXPORT ? 'export' : 'standalone',

  images: IS_STATIC_EXPORT
    ? { unoptimized: true }  // 静态导出不支持图片优化
    : { remotePatterns },

  // 生产环境自动移除 console.log（保留 error 和 warn）
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production' ? { exclude: ['error', 'warn'] } : false,
  },

  // 静态导出需要尾部斜杠
  ...(IS_STATIC_EXPORT ? { trailingSlash: true } : {}),
}

// 非静态导出模式：使用 rewrites 代理 API 请求，消除 CORS
if (!IS_STATIC_EXPORT) {
  nextConfig.rewrites = async () => [
    { source: '/api/:path*', destination: `${API_BASE}/api/:path*` },
    { source: '/health', destination: `${API_BASE}/health` },
    { source: '/uploads/:path*', destination: `${API_BASE}/uploads/:path*` },
  ]
  // 增加代理超时，避免 AI 调用耗时较长时返回 500
  nextConfig.experimental = {
    ...nextConfig.experimental,
    proxyTimeout: 120000, // 2 分钟
  }
}

module.exports = nextConfig
