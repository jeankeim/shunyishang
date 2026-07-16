'use client'

import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useUserStore } from '@/store/user'
import { ConfirmDialog } from '@/components/ui'
import {
  getCommunityPosts,
  createCommunityPost,
  togglePostLike,
  deleteCommunityPost,
  getPostComments,
  createPostComment,
} from '@/lib/api'

// 五行筛选标签
const ELEMENT_TABS = [
  { id: '', label: '全部', emoji: '✨' },
  { id: '金', label: '金', emoji: '🪙' },
  { id: '木', label: '木', emoji: '🌱' },
  { id: '水', label: '水', emoji: '💧' },
  { id: '火', label: '火', emoji: '🔥' },
  { id: '土', label: '土', emoji: '🏔️' },
]

interface Post {
  id: number
  user_id: number
  diary_id?: number
  content: string
  image_urls: string[]
  tags: string[]
  element?: string
  view_count: number
  like_count: number
  comment_count: number
  is_featured: boolean
  published_at: string
  is_liked: boolean
  author_name?: string
  author_avatar?: string
}

interface Comment {
  id: number
  user_id: number
  content: string
  parent_id?: number
  created_at: string
  author_name?: string
}

export default function CommunityPage() {
  const { isAuthenticated } = useUserStore()

  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [activeElement, setActiveElement] = useState('')

  // 发布弹窗
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newContent, setNewContent] = useState('')
  const [newTags, setNewTags] = useState('')
  const [newElement, setNewElement] = useState('')
  const [publishing, setPublishing] = useState(false)

  // 评论
  const [activePostId, setActivePostId] = useState<number | null>(null)
  const [comments, setComments] = useState<Comment[]>([])
  const [newComment, setNewComment] = useState('')
  const [commenting, setCommenting] = useState(false)

  // 删除确认
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)

  // 加载帖子
  const fetchPosts = useCallback(async (p = 1, element = '') => {
    if (!isAuthenticated) return
    setLoading(true)
    try {
      const data = await getCommunityPosts(p, 20, element || undefined)
      if (p === 1) {
        setPosts(data.posts || [])
      } else {
        setPosts(prev => [...prev, ...(data.posts || [])])
      }
      setTotal(data.total || 0)
      setPage(p)
    } catch (e) {
      console.error('获取帖子失败:', e)
    } finally {
      setLoading(false)
    }
  }, [isAuthenticated])

  useEffect(() => {
    if (isAuthenticated) fetchPosts(1, activeElement)
  }, [isAuthenticated, activeElement, fetchPosts])

  // 发布帖子
  const handlePublish = async () => {
    if (!newContent.trim() || publishing) return
    setPublishing(true)
    try {
      await createCommunityPost({
        content: newContent.trim(),
        tags: newTags.split(/[,，\s]+/).filter(Boolean),
        element: newElement || undefined,
      })
      setNewContent('')
      setNewTags('')
      setNewElement('')
      setShowCreateModal(false)
      fetchPosts(1, activeElement)
    } catch (e: any) {
      alert(e.message || '发布失败')
    } finally {
      setPublishing(false)
    }
  }

  // 点赞
  const handleLike = async (postId: number) => {
    try {
      const result = await togglePostLike(postId)
      setPosts(prev =>
        prev.map(p =>
          p.id === postId
            ? {
                ...p,
                is_liked: result.action === 'liked',
                like_count: result.action === 'liked' ? p.like_count + 1 : Math.max(p.like_count - 1, 0),
              }
            : p
        )
      )
    } catch (e) {
      console.error('点赞失败:', e)
    }
  }

  // 删除帖子
  const handleDelete = async (postId: number) => {
    setConfirmDeleteId(postId)
  }

  const doDeletePost = async () => {
    if (!confirmDeleteId) return
    try {
      await deleteCommunityPost(confirmDeleteId)
      setPosts(prev => prev.filter(p => p.id !== confirmDeleteId))
    } catch (e) {
      console.error('删除失败:', e)
    } finally {
      setConfirmDeleteId(null)
    }
  }

  // 打开评论
  const openComments = async (postId: number) => {
    setActivePostId(postId)
    try {
      const data = await getPostComments(postId)
      setComments(data.comments || [])
    } catch (e) {
      console.error('获取评论失败:', e)
    }
  }

  // 发评论
  const handleComment = async () => {
    if (!newComment.trim() || !activePostId || commenting) return
    setCommenting(true)
    try {
      const c = await createPostComment(activePostId, { content: newComment.trim() })
      setComments(prev => [...prev, c])
      setNewComment('')
      setPosts(prev =>
        prev.map(p => (p.id === activePostId ? { ...p, comment_count: p.comment_count + 1 } : p))
      )
    } catch (e: any) {
      alert(e.message || '评论失败')
    } finally {
      setCommenting(false)
    }
  }

  // 加载更多
  const loadMore = () => {
    if (!loading && posts.length < total) {
      fetchPosts(page + 1, activeElement)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="max-w-lg mx-auto text-center py-16">
        <p className="text-5xl mb-4">🏛️</p>
        <h2 className="text-lg font-semibold text-stone-800 mb-2">穿搭广场</h2>
        <p className="text-sm text-stone-500">登录后即可浏览和分享穿搭灵感</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto pb-8">
      {/* 顶部标题 */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-stone-800">穿搭广场</h1>
          <p className="text-xs text-stone-500 mt-0.5">分享穿搭灵感，发现五行穿搭美学</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl text-sm font-medium shadow-md hover:shadow-lg transition-all hover:-translate-y-0.5"
        >
          + 发布穿搭
        </button>
      </div>

      {/* 五行筛选标签 */}
      <div className="flex gap-2 mb-5 overflow-x-auto pb-1">
        {ELEMENT_TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveElement(tab.id)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
              activeElement === tab.id
                ? 'bg-amber-100 text-amber-700 border border-amber-200'
                : 'bg-stone-50 text-stone-500 border border-stone-200 hover:bg-stone-100'
            }`}
          >
            <span>{tab.emoji}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* 帖子列表 */}
      {posts.length === 0 && !loading ? (
        <div className="text-center py-16">
          <p className="text-4xl mb-3">🌿</p>
          <p className="text-sm text-stone-500">还没有人发布穿搭，成为第一个分享的人吧！</p>
        </div>
      ) : (
        <div className="space-y-4">
          {posts.map((post, idx) => (
            <PostCard
              key={post.id}
              post={post}
              index={idx}
              onLike={() => handleLike(post.id)}
              onDelete={() => handleDelete(post.id)}
              onComment={() => openComments(post.id)}
            />
          ))}
        </div>
      )}

      {/* 加载更多 */}
      {posts.length < total && (
        <div className="text-center mt-6">
          <button
            onClick={loadMore}
            disabled={loading}
            className="px-6 py-2 text-sm text-stone-500 hover:text-stone-700 border border-stone-200 rounded-xl hover:bg-stone-50 transition-all disabled:opacity-50"
          >
            {loading ? '加载中...' : '加载更多'}
          </button>
        </div>
      )}

      {/* 发布弹窗 */}
      <AnimatePresence>
        {showCreateModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 backdrop-blur-sm"
            onClick={() => setShowCreateModal(false)}
          >
            <motion.div
              initial={{ y: 100, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 100, opacity: 0 }}
              className="w-full max-w-lg bg-white rounded-t-2xl sm:rounded-2xl p-6 shadow-2xl"
              onClick={e => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold text-stone-800 mb-4">分享穿搭</h3>

              <textarea
                value={newContent}
                onChange={e => setNewContent(e.target.value)}
                placeholder="分享你的穿搭心得..."
                maxLength={1000}
                className="w-full h-32 p-3 border border-stone-200 rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-amber-300"
              />

              <div className="flex gap-3 mt-3">
                <select
                  value={newElement}
                  onChange={e => setNewElement(e.target.value)}
                  className="px-3 py-2 border border-stone-200 rounded-lg text-sm"
                >
                  <option value="">选择五行</option>
                  {['金', '木', '水', '火', '土'].map(el => (
                    <option key={el} value={el}>{el}</option>
                  ))}
                </select>
                <input
                  value={newTags}
                  onChange={e => setNewTags(e.target.value)}
                  placeholder="标签（空格分隔）"
                  className="flex-1 px-3 py-2 border border-stone-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-300"
                />
              </div>

              <div className="flex gap-3 mt-4">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 py-2.5 border border-stone-200 rounded-xl text-sm text-stone-600 hover:bg-stone-50"
                >
                  取消
                </button>
                <button
                  onClick={handlePublish}
                  disabled={!newContent.trim() || publishing}
                  className="flex-1 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl text-sm font-medium disabled:opacity-50"
                >
                  {publishing ? '发布中...' : '发布'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 评论弹窗 */}
      <AnimatePresence>
        {activePostId !== null && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 backdrop-blur-sm"
            onClick={() => setActivePostId(null)}
          >
            <motion.div
              initial={{ y: 100, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 100, opacity: 0 }}
              className="w-full max-w-lg bg-white rounded-t-2xl sm:rounded-2xl p-6 shadow-2xl max-h-[70vh] flex flex-col"
              onClick={e => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold text-stone-800 mb-3">
                评论 ({comments.length})
              </h3>

              <div className="flex-1 overflow-y-auto space-y-3 mb-4">
                {comments.length === 0 ? (
                  <p className="text-sm text-stone-400 text-center py-8">暂无评论</p>
                ) : (
                  comments.map(c => (
                    <div key={c.id} className="flex gap-2">
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-amber-200 to-orange-200 flex items-center justify-center text-xs shrink-0">
                        {c.author_name?.[0] || '👤'}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-stone-700">{c.author_name || '用户'}</span>
                          <span className="text-xs text-stone-400">
                            {new Date(c.created_at).toLocaleDateString('zh-CN')}
                          </span>
                        </div>
                        <p className="text-sm text-stone-600 mt-0.5">{c.content}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="flex gap-2">
                <input
                  value={newComment}
                  onChange={e => setNewComment(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleComment()}
                  placeholder="写评论..."
                  maxLength={500}
                  className="flex-1 px-3 py-2 border border-stone-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-300"
                />
                <button
                  onClick={handleComment}
                  disabled={!newComment.trim() || commenting}
                  className="px-4 py-2 bg-amber-500 text-white rounded-xl text-sm disabled:opacity-50"
                >
                  {commenting ? '...' : '发送'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 删除确认弹窗 */}
      <ConfirmDialog
        isOpen={confirmDeleteId !== null}
        onClose={() => setConfirmDeleteId(null)}
        onConfirm={doDeletePost}
        title="删除帖子"
        description="确定删除这条帖子吗？此操作不可撤销。"
        confirmText="删除"
        danger
      />
    </div>
  )
}

// ========== 帖子卡片组件 ==========
function PostCard({
  post,
  index,
  onLike,
  onDelete,
  onComment,
}: {
  post: Post
  index: number
  onLike: () => void
  onDelete: () => void
  onComment: () => void
}) {
  const { user } = useUserStore()
  const isOwner = user?.id === post.user_id

  const elementColors: Record<string, string> = {
    '金': 'from-gray-200 to-yellow-200',
    '木': 'from-green-200 to-emerald-300',
    '水': 'from-blue-200 to-cyan-300',
    '火': 'from-red-200 to-orange-300',
    '土': 'from-amber-200 to-yellow-300',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.05, 0.3), duration: 0.3 }}
      className="bg-white rounded-2xl border border-stone-200/60 shadow-sm overflow-hidden hover:shadow-md transition-shadow"
    >
      {/* 作者信息 */}
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-200 to-orange-200 flex items-center justify-center text-sm">
            {post.author_name?.[0] || '👤'}
          </div>
          <div>
            <p className="text-sm font-medium text-stone-700">{post.author_name || '用户'}</p>
            <p className="text-xs text-stone-400">
              {new Date(post.published_at).toLocaleDateString('zh-CN')}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {post.element && (
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium bg-gradient-to-r ${elementColors[post.element] || 'from-stone-200 to-stone-300'} text-stone-700`}>
              {post.element}
            </span>
          )}
          {post.is_featured && (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
              精选
            </span>
          )}
          {post.diary_id && (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-600 border border-emerald-100">
              来自日记
            </span>
          )}
          {isOwner && (
            <button onClick={onDelete} className="text-stone-400 hover:text-red-500 text-xs">
              删除
            </button>
          )}
        </div>
      </div>

      {/* 图片 */}
      {post.image_urls.length > 0 && (
        <div className={`grid gap-0.5 ${post.image_urls.length === 1 ? 'grid-cols-1' : 'grid-cols-2'} px-4`}>
          {post.image_urls.slice(0, 4).map((url, i) => (
            <div
              key={i}
              className="aspect-square bg-stone-100 rounded-lg overflow-hidden"
              style={{ backgroundImage: `url(${url})`, backgroundSize: 'cover', backgroundPosition: 'center' }}
            />
          ))}
        </div>
      )}

      {/* 内容 */}
      <div className="px-4 py-3">
        <p className="text-sm text-stone-700 leading-relaxed whitespace-pre-wrap">{post.content}</p>
        {post.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {post.tags.map((tag, i) => (
              <span key={i} className="px-2 py-0.5 bg-stone-100 text-stone-500 rounded-full text-xs">
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 互动栏 */}
      <div className="flex items-center gap-4 px-4 pb-3 pt-1 border-t border-stone-100">
        <button
          onClick={onLike}
          className={`flex items-center gap-1.5 text-sm transition-colors ${
            post.is_liked ? 'text-red-500' : 'text-stone-400 hover:text-red-400'
          }`}
        >
          <svg className="w-4 h-4" fill={post.is_liked ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
          <span>{post.like_count > 0 ? post.like_count : ''}</span>
        </button>

        <button
          onClick={onComment}
          className="flex items-center gap-1.5 text-sm text-stone-400 hover:text-amber-500 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <span>{post.comment_count > 0 ? post.comment_count : ''}</span>
        </button>

        <span className="text-xs text-stone-300 ml-auto">{post.view_count} 浏览</span>
      </div>
    </motion.div>
  )
}
