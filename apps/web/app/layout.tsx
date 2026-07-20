import type { Metadata, Viewport } from 'next'
import { Noto_Sans_SC } from 'next/font/google'
import './globals.css'
import './accessibility.css'
import { ThemeProvider } from '@/components/providers/ThemeProvider'
import { ToastProvider } from '@/components/providers/ToastProvider'

// 自托管字体，避免 Google Fonts CDN 阻塞渲染（国内网络不可达）
const notoSansSC = Noto_Sans_SC({
  subsets: ['latin'],
  weight: ['300', '400', '500', '700'],
  display: 'swap',
  variable: '--font-noto-sans-sc',
})

export const metadata: Metadata = {
  title: '顺衣尚 - 五行智能衣橱',
  description: '基于八字与五行的智能穿搭推荐',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: '顺衣尚',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#3DA35D' },
    { media: '(prefers-color-scheme: dark)', color: '#2D4A38' },
  ],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" data-theme="light" suppressHydrationWarning>
      <head>
        {/* PWA meta tags */}
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="顺衣尚" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
      </head>
      <body className={`${notoSansSC.variable} font-sans`} suppressHydrationWarning>
        {/* 清理可能损坏的localStorage数据 */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  const stores = ['wuxing-user-storage', 'wuxing-chat-storage', 'wuxing-wardrobe-storage'];
                  stores.forEach(function(storeName) {
                    var data = localStorage.getItem(storeName);
                    if (data) {
                      try {
                        JSON.parse(data);
                      } catch (e) {
                        console.warn('清理损坏的localStorage:', storeName);
                        localStorage.removeItem(storeName);
                      }
                    }
                  });
                } catch (e) {
                  console.error('localStorage清理失败:', e);
                }
              })();
            `,
          }}
        />
        <ThemeProvider>
          <ToastProvider>
            {children}
          </ToastProvider>
        </ThemeProvider>
        
        {/* Service Worker：仅生产环境注册，开发环境注销避免缓存干扰热更新 */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  if (${process.env.NODE_ENV === 'production'}) {
                    // 生产环境：注册 SW
                    navigator.serviceWorker.register('/sw.js')
                      .catch(function(error) {
                        console.error('[PWA] SW 注册失败:', error);
                      });
                  } else {
                    // 开发环境：注销所有 SW，清除缓存
                    navigator.serviceWorker.getRegistrations().then(function(registrations) {
                      registrations.forEach(function(reg) { reg.unregister(); });
                    });
                    caches.keys().then(function(names) {
                      names.forEach(function(name) { caches.delete(name); });
                    });
                  }
                });
              }
            `,
          }}
        />
      </body>
    </html>
  )
}
