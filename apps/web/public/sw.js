// Service Worker for PWA - 离线缓存支持
const CACHE_NAME = 'shunyishang-v1'
const OFFLINE_URL = '/offline.html'

// 需要预缓存的关键资源
const PRECACHE_URLS = [
  '/',
  '/manifest.json',
  '/offline.html',
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
    })
  )
  self.clients.claim()
})

// 网络请求拦截 - 缓存优先策略
self.addEventListener('fetch', (event) => {
  // 跳过非 GET 请求
  if (event.request.method !== 'GET') return

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
          // 只缓存成功响应和 http/https 请求
          if (!response || response.status !== 200 || event.request.url.startsWith('http')) {
            return response
          }

          const responseClone = response.clone()
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone)
          })

          return response
        })
        .catch(() => {
          // 网络失败，返回离线页面
          if (event.request.destination === 'document') {
            return caches.match(OFFLINE_URL)
          }
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
