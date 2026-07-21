/**
 * 多皮肤注册表 - 东方玄学/五行主题
 * 皮肤仅覆盖 globals.css 中的设计令牌（CSS 变量），组件零改动即可全站生效。
 * - light 皮肤：清空/设置 data-skin，移除 .dark
 * - dark 皮肤：设置 data-skin + 添加 .dark（复用组件已有的 dark: 工具类）
 */

export type SkinId = 'auto' | 'xuan' | 'tianqing' | 'violet' | 'jade'
export type SkinMode = 'light' | 'dark'

export interface SkinDef {
  id: SkinId
  name: string
  desc: string
  mode: SkinMode
  /** 预览色：[底色, 强调色] */
  swatch: [string, string]
}

export const SKINS: SkinDef[] = [
  {
    id: 'auto',
    name: '节气·青瓷',
    desc: '跟随节气的低饱和青瓷绿（默认）',
    mode: 'light',
    swatch: ['#f6faf7', '#4E8560'],
  },
  {
    id: 'xuan',
    name: '宣纸·墨韵',
    desc: '暖白宣纸 + 墨黑 + 朱砂，水墨新中式',
    mode: 'light',
    swatch: ['#f7f3ea', '#A8443A'],
  },
  {
    id: 'tianqing',
    name: '天青·素雅',
    desc: '冷调天青白 + 黛蓝，清冷雅致',
    mode: 'light',
    swatch: ['#f2f6f8', '#4F7D9E'],
  },
  {
    id: 'violet',
    name: '玄光·紫夜',
    desc: '深空紫黑 + 香槟金，神秘玄学',
    mode: 'dark',
    swatch: ['#17132b', '#e4c892'],
  },
  {
    id: 'jade',
    name: '静奢·墨玉',
    desc: '墨绿藏青曜石 + 暖金，低调静奢',
    mode: 'dark',
    swatch: ['#10201c', '#d8c58f'],
  },
]

export const DEFAULT_SKIN: SkinId = 'auto'

export function getSkin(id: string): SkinDef {
  return SKINS.find((s) => s.id === id) ?? SKINS[0]
}

/** 将皮肤应用到 <html>：设置 data-skin 并按需切换 .dark */
export function applySkin(id: string) {
  if (typeof document === 'undefined') return
  const el = document.documentElement
  const skin = getSkin(id)
  if (skin.id === 'auto') {
    // 回落到节气自动主题（由 useWuxingTheme 驱动 data-element）
    el.removeAttribute('data-skin')
    el.classList.remove('dark')
  } else {
    el.setAttribute('data-skin', skin.id)
    el.classList.toggle('dark', skin.mode === 'dark')
  }
}
