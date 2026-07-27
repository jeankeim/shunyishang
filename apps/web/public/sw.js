// Service Worker for PWA - 离线缓存支持
// v3: HTML 改为网络优先，修复部署后旧缓存 HTML 引用已删除 chunk 导致的 ChunkLoadError
const CACHE_NAME = 'shunyishang-v3'
const OFFLINE_URL = '/offline.html'

// 需要预缓存的关键资源（不预缓存 '/'：HTML 必须网络优先，避免版本不一致）
const PRECACHE_URLS = [
  '/manifest.json',
  '/offline.html',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/favicon.ico',
]

// 安装事件 - 预缓存关键资源
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] 预缓存关键资源')
      return cache.addAll(PRECACHE_URLS)
    })
  )
  self.skipWaiting()
})

// 激活事件 - 清理旧缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      )
    }).then(() => self.clients.claim())
  )
})

// 网络请求拦截
// 策略：HTML 文档网络优先（保证拿到最新版本）；带 hash 的静态资源缓存优先；API 网络优先
self.addEventListener('fetch', (event) => {
  // 跳过非 GET 请求
  if (event.request.method !== 'GET') return

  // HTML 文档（页面导航）- 网络优先，失败才回退缓存/离线页
  // 否则部署新版后旧 HTML 会引用已被替换的 chunk，导致 ChunkLoadError
  if (event.request.mode === 'navigate' || event.request.destination === 'document') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const responseClone = response.clone()
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone)
          })
          return response
        })
        .catch(() => {
          return caches.match(event.request).then((cached) => {
            return cached || caches.match(OFFLINE_URL)
          })
        })
    )
    return
  }

  // Next.js RSC 导航载荷（?_rsc=）- 直连网络不缓存，旧载荷同样会引用失效 chunk
  if (event.request.url.includes('_rsc=')) {
    return
  }

  // API 请求 - 网络优先
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // 缓存成功的 API 响应
          const responseClone = response.clone()
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone)
          })
          return response
        })
        .catch(() => {
          // API 失败时返回缓存
          return caches.match(event.request)
        })
    )
    return
  }

  // 静态资源 - 缓存优先
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse
      }

      // 缓存未命中，从网络获取
      return fetch(event.request)
        .then((response) => {
          // 只缓存成功响应（跳过非 http/https 协议如 chrome-extension、blob、data）
          if (!response || response.status !== 200 || !event.request.url.startsWith('http')) {
            return response
          }

          const responseClone = response.clone()
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone)
          })

          return response
        })
        .catch(() => {
          // 网络失败，文档请求返回离线页面，其他请求返回 404
          if (event.request.destination === 'document') {
            return caches.match(OFFLINE_URL)
          }
          return new Response('', { status: 404, statusText: 'Not Found' })
        })
    })
  )
})

// 后台同步（可选）
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-wardrobe') {
    event.waitUntil(syncWardrobe())
  }
})

async function syncWardrobe() {
  // 离线时保存的衣橱操作，在联网后同步
  console.log('[SW] 后台同步衣橱数据')
}
