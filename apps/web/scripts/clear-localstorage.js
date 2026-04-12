/**
 * 清理可能损坏的localStorage数据
 * 在浏览器控制台运行此脚本
 */

console.log('🧹 开始清理localStorage...')

// 检查并清理可能损坏的store数据
const storesToCheck = [
  'wuxing-user-storage',
  'wuxing-chat-storage', 
  'wuxing-wardrobe-storage'
]

storesToCheck.forEach(storeName => {
  const data = localStorage.getItem(storeName)
  if (data) {
    try {
      const parsed = JSON.parse(data)
      console.log(`✅ ${storeName}: 数据格式正常`, parsed)
    } catch (error) {
      console.error(`❌ ${storeName}: 数据损坏，正在清理...`, error)
      localStorage.removeItem(storeName)
      console.log(`✅ ${storeName}: 已清理`)
    }
  } else {
    console.log(`ℹ️  ${storeName}: 不存在`)
  }
})

console.log('✨ 清理完成！请刷新页面。')
