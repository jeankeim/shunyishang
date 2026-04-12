import type { Metadata } from 'next'
import './globals.css'
import { ThemeProvider } from '@/components/providers/ThemeProvider'
import { ToastProvider } from '@/components/providers/ToastProvider'

export const metadata: Metadata = {
  title: '顺衣尚 - 五行智能衣橱',
  description: '基于八字与五行的智能穿搭推荐',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
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
      </body>
    </html>
  )
}
