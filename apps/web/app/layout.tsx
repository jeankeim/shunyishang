import type { Metadata } from 'next'
import './globals.css'
import { ThemeProvider } from '@/components/providers/ThemeProvider'
import { ToastProvider } from '@/components/providers/ToastProvider'

export const metadata: Metadata = {
  title: '顺衣尚 - 五行智能衣橱',
  description: '基于八字与五行的智能穿搭推荐',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: '顺衣尚',
  },
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
    userScalable: false,
  },
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
    <html lang="zh-CN">
      <head>
        {/* PWA meta tags */}
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="顺衣尚" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
      </head>
      <body className="font-sans">
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
        
        {/* 注册 Service Worker */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js')
                    .then(function(registration) {
                      console.log('[PWA] Service Worker 注册成功:', registration.scope);
                    })
                    .catch(function(error) {
                      console.log('[PWA] Service Worker 注册失败:', error);
                    });
                });
              }
            `,
          }}
        />
      </body>
    </html>
  )
}
