/**
 * 宋锦国风海报 Satori 同构模板（阶段2）
 * 纯 JSX + 内联样式（Flexbox 子集），由 Next.js API Route 经
 * Satori → SVG → resvg PNG 输出 1080×1920 分享海报。
 *
 * 与后端 Pillow 版（poster_service.generate_guofeng_poster）布局对齐：
 * 印章/回纹带/主标题/引言/主件大视觉/单品清单/五行相生环带/品牌页脚。
 */
import type { ReactNode } from 'react'

// ---------- 数据类型 ----------

export interface SatoriPosterItem {
  name: string
  image_data?: string        // data URI（route 端预取，避免 Satori 跨域）
  primary_element?: string
  category?: string
  reason?: string
}

export interface SatoriPosterData {
  title: string
  items: SatoriPosterItem[]
  xiyong_elements: string[]
  theme: string
  quote?: string
  username?: string
  lunar?: string             // 如「丙午年六月廿三」
  date: string               // 公历 YYYY-MM-DD
  paper_texture_data?: string // 宣纸纹理 data URI
}

// ---------- 与后端 GUOFENG_THEMES 保持一致 ----------

export const SATORI_GUOFENG_THEMES: Record<string, {
  primary: string; ink_dark: string; paper: string
}> = {
  wood:  { primary: '#4E8560', ink_dark: '#33593F', paper: '#F6F3E9' },
  fire:  { primary: '#A85D57', ink_dark: '#6E3A35', paper: '#F8F1E8' },
  earth: { primary: '#9C8654', ink_dark: '#6B5A36', paper: '#F8F3E6' },
  metal: { primary: '#8FA3AB', ink_dark: '#5C6E76', paper: '#F7F5EF' },
  water: { primary: '#4F7D9E', ink_dark: '#33536B', paper: '#F5F3EA' },
}

const SEAL_RED = '#A63D2F'
const INK = '#2B2B2B'
const ANTIQUE_GOLD = '#B08D57'
const INK_GRAY = '#7A7468'

export const SATORI_ELEMENT_COLORS: Record<string, string> = {
  '木': '#4E8560', '火': '#A85D57', '土': '#9C8654',
  '金': '#8FA3AB', '水': '#3F6C8E',
}

const MAIN_PRIORITY = ['外套', '连衣裙', '裙装', '上装']

export function pickSatoriMainIndex(items: SatoriPosterItem[]): number {
  for (const cat of MAIN_PRIORITY) {
    const i = items.findIndex((it) => it.category === cat)
    if (i >= 0) return i
  }
  return 0
}

/** 按字号估算截断（中文全角=字号宽，ASCII 半角） */
export function truncateText(text: string, fontSize: number, maxWidth: number): string {
  let width = 0
  for (let i = 0; i < text.length; i++) {
    width += text.charCodeAt(i) > 0xff ? fontSize : fontSize * 0.55
    if (width > maxWidth) return text.slice(0, i) + '…'
  }
  return text
}

/** 按字号估算折行 */
export function wrapSatoriText(text: string, fontSize: number, maxWidth: number): string[] {
  const lines: string[] = []
  let line = ''
  let width = 0
  for (const ch of text) {
    const w = ch.charCodeAt(0) > 0xff ? fontSize : fontSize * 0.55
    if (width + w > maxWidth && line) {
      lines.push(line)
      line = ch
      width = w
    } else {
      line += ch
      width += w
    }
  }
  if (line) lines.push(line)
  return lines
}

// ---------- 原子组件 ----------

const FONT = 'PosterSerif'

function Seal({ char, size, fontSize }: { char: string; size: number; fontSize: number }): ReactNode {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: Math.round(size / 10),
        backgroundColor: SEAL_RED,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#FFFFFF',
        fontSize,
        fontFamily: FONT,
        flexShrink: 0,
      }}
    >
      {char}
    </div>
  )
}

function MeanderBand({ width }: { width: number }): ReactNode {
  // 回纹近似：古铜金双细线夹回旋纹样（repeating 渐变模拟）
  return (
    <div style={{ display: 'flex', flexDirection: 'column', width, alignItems: 'center' }}>
      <div style={{ width: '100%', height: 2, backgroundColor: ANTIQUE_GOLD }} />
      <div
        style={{
          width: '100%',
          height: 18,
          display: 'flex',
          backgroundImage:
            `repeating-linear-gradient(90deg, ${ANTIQUE_GOLD} 0px, ${ANTIQUE_GOLD} 2px, transparent 2px, transparent 8px, ${ANTIQUE_GOLD} 8px, ${ANTIQUE_GOLD} 10px, transparent 10px, transparent 24px)`,
        }}
      />
      <div style={{ width: '100%', height: 2, backgroundColor: ANTIQUE_GOLD }} />
    </div>
  )
}

function InkBlob({ x, y, size, color, alpha }: {
  x: number; y: number; size: number; color: string; alpha: number
}): ReactNode {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(color.slice(i, i + 2), 16))
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: size,
        height: size,
        borderRadius: '50%',
        backgroundImage:
          `radial-gradient(circle at 50% 50%, rgba(${r},${g},${b},${alpha}) 0%, rgba(${r},${g},${b},${alpha * 0.5}) 45%, rgba(${r},${g},${b},0) 72%)`,
      }}
    />
  )
}

function ElementCircle({ elem, active }: { elem: string; active: boolean }): ReactNode {
  return (
    <div
      style={{
        width: 76,
        height: 76,
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 32,
        fontFamily: FONT,
        flexShrink: 0,
        ...(active
          ? { backgroundColor: SATORI_ELEMENT_COLORS[elem], color: '#FFFFFF' }
          : { color: '#B5AEA0', border: '2px solid #C9C2B4' }),
      }}
    >
      {elem}
    </div>
  )
}

// ---------- 主模板 ----------

export function GuofengSatori(data: SatoriPosterData): ReactNode {
  const theme = SATORI_GUOFENG_THEMES[data.theme] || SATORI_GUOFENG_THEMES.fire
  const items = (data.items || []).slice(0, 6)
  const mainIdx = items.length ? pickSatoriMainIndex(items) : -1
  const hero = mainIdx >= 0 ? items[mainIdx] : undefined
  const rest = items.filter((_, i) => i !== mainIdx).slice(0, 5)
  const showQuote = !!data.quote && items.length <= 4
  const heroSize = items.length >= 5 ? 360 : 400
  const sealChar = data.xiyong_elements?.[0] || '衣'

  const activeElems = new Set<string>([
    ...(data.xiyong_elements || []),
    ...items.map((it) => it.primary_element).filter(Boolean) as string[],
  ])
  const elementOrder = ['木', '火', '土', '金', '水']

  return (
    <div
      style={{
        width: 1080,
        height: 1920,
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: theme.paper,
        ...(data.paper_texture_data
          ? { backgroundImage: `url(${data.paper_texture_data})` }
          : {}),
        position: 'relative',
        fontFamily: FONT,
        color: INK,
      }}
    >
      {/* 水墨晕染（四角，主题色与墨色交替） */}
      <InkBlob x={-220} y={-260} size={820} color={theme.ink_dark} alpha={0.2} />
      <InkBlob x={640} y={-220} size={760} color={theme.primary} alpha={0.16} />
      <InkBlob x={-280} y={1560} size={780} color={theme.primary} alpha={0.1} />
      <InkBlob x={700} y={1600} size={760} color={theme.ink_dark} alpha={0.1} />

      {/* 顶部回纹带 */}
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 44 }}>
        <MeanderBand width={900} />
      </div>

      {/* 印章 + 标题 + 竖排农历 */}
      <div style={{ display: 'flex', flexDirection: 'row', marginTop: 24, padding: '0 90px' }}>
        <div style={{ width: 150, display: 'flex', paddingTop: 6 }}>
          <Seal char={sealChar} size={104} fontSize={52} />
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div style={{ display: 'flex', fontSize: 76, fontFamily: FONT, color: INK, letterSpacing: 4 }}>
            {truncateText(data.title, 76, 700)}
          </div>
        </div>
        <div style={{ width: 150, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', paddingTop: 8 }}>
          {(data.lunar || '').split('').slice(0, 9).map((ch, i) => (
            <div key={i} style={{ fontSize: 26, color: INK_GRAY, lineHeight: '36px', fontFamily: FONT }}>
              {ch}
            </div>
          ))}
        </div>
      </div>

      {/* 金线菱形分隔 */}
      <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: 24 }}>
        <div style={{ width: 230, height: 2, backgroundColor: ANTIQUE_GOLD }} />
        <div
          style={{
            width: 16, height: 16, margin: '0 24px',
            backgroundColor: theme.primary,
            transform: 'rotate(45deg)',
          }}
        />
        <div style={{ width: 230, height: 2, backgroundColor: ANTIQUE_GOLD }} />
      </div>

      {/* 副标题 */}
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 22 }}>
        <div style={{ fontSize: 32, color: theme.primary, fontFamily: FONT, letterSpacing: 6 }}>
          五行相生 · 顺势而衣
        </div>
      </div>

      {/* 引言（≤4 件时展示） */}
      {showQuote ? (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 30, padding: '0 130px' }}>
          <div style={{ width: 3, backgroundColor: ANTIQUE_GOLD, marginRight: 26 }} />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            {wrapSatoriText(data.quote || '', 28, 720).slice(0, 2).map((line, i) => (
              <div key={i} style={{ fontSize: 28, color: '#4A4438', lineHeight: '44px', fontFamily: FONT }}>
                {line}
              </div>
            ))}
          </div>
          <div style={{ width: 3, backgroundColor: ANTIQUE_GOLD, marginLeft: 26 }} />
        </div>
      ) : null}

      {/* 衣单区标题 */}
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: showQuote ? 34 : 44 }}>
        <div style={{ fontSize: 28, color: ANTIQUE_GOLD, fontFamily: FONT, letterSpacing: 2 }}>
          {data.username ? `· ${data.username} 的今日衣单 ·` : '· 今日衣单 ·'}
        </div>
      </div>

      {/* 主件大视觉 + 信息列 */}
      {hero ? (
        <div style={{ display: 'flex', flexDirection: 'row', marginTop: 30, padding: '0 90px' }}>
          <div
            style={{
              width: heroSize,
              height: heroSize,
              borderRadius: 16,
              border: `3px solid ${ANTIQUE_GOLD}`,
              padding: 10,
              display: 'flex',
              flexShrink: 0,
              backgroundColor: '#FFFDF6',
            }}
          >
            <div
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: `1px solid ${theme.primary}`,
                borderRadius: 10,
                overflow: 'hidden',
              }}
            >
              {hero.image_data ? (
                <img src={hero.image_data} width={heroSize - 28} height={heroSize - 28} style={{ objectFit: 'cover' }} />
              ) : (
                <div style={{ display: 'flex', fontSize: 88, color: theme.ink_dark, fontFamily: FONT }}>
                  {hero.primary_element || '衣'}
                </div>
              )}
            </div>
          </div>

          {/* 信息列 */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', marginLeft: 48, paddingTop: 16 }}>
            {wrapSatoriText(hero.name || '', 36, 430).slice(0, 2).map((line, i) => (
              <div key={i} style={{ fontSize: 36, color: INK, lineHeight: '48px', fontFamily: FONT }}>
                {line}
              </div>
            ))}
            <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', marginTop: 16 }}>
              {hero.primary_element ? (
                <Seal char={hero.primary_element} size={44} fontSize={24} />
              ) : null}
              {hero.category ? (
                <div
                  style={{
                    ...(hero.primary_element ? { marginLeft: 14 } : {}),
                    border: `2px solid ${ANTIQUE_GOLD}`,
                    borderRadius: 6,
                    padding: '4px 16px',
                    fontSize: 24,
                    color: INK_GRAY,
                    fontFamily: FONT,
                  }}
                >
                  {hero.category}
                </div>
              ) : null}
            </div>
            {hero.reason ? (
              <div style={{ display: 'flex', flexDirection: 'column', marginTop: 22 }}>
                {wrapSatoriText(hero.reason, 24, 430).slice(0, 3).map((line, i) => (
                  <div key={i} style={{ fontSize: 24, color: INK_GRAY, lineHeight: '38px', fontFamily: FONT }}>
                    {line}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* 单品清单 */}
      <div style={{ display: 'flex', flexDirection: 'column', marginTop: 28, padding: '0 90px' }}>
        {rest.map((sub, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'center',
              backgroundColor: '#FFFDF6',
              border: '2px solid rgba(176,141,87,0.47)',
              borderRadius: 14,
              padding: '10px 22px',
              marginBottom: 12,
            }}
          >
            <div
              style={{
                width: 92,
                height: 92,
                borderRadius: 8,
                overflow: 'hidden',
                backgroundColor: '#F3EFE2',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              {sub.image_data ? (
                <img src={sub.image_data} width={92} height={92} style={{ objectFit: 'cover' }} />
              ) : (
                <div style={{ display: 'flex', fontSize: 40, color: theme.ink_dark, fontFamily: FONT }}>
                  {sub.primary_element || '衣'}
                </div>
              )}
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', marginLeft: 24 }}>
              <div style={{ fontSize: 28, color: INK, fontFamily: FONT }}>
                {truncateText(sub.name || '', 28, 430)}
              </div>
              {[sub.category, sub.reason ? truncateText(sub.reason, 21, 330) : ''].filter(Boolean).length > 0 ? (
                <div style={{ fontSize: 21, color: INK_GRAY, marginTop: 8, fontFamily: FONT }}>
                  {[sub.category, sub.reason ? truncateText(sub.reason, 21, 330) : ''].filter(Boolean).join(' · ')}
                </div>
              ) : null}
            </div>
            {sub.primary_element ? (
              <Seal char={sub.primary_element} size={40} fontSize={22} />
            ) : null}
          </div>
        ))}
      </div>

      {/* 五行相生环带（吸底） */}
      <div style={{ display: 'flex', flex: 1 }} />
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingBottom: 8 }}>
        <div style={{ fontSize: 24, color: ANTIQUE_GOLD, fontFamily: FONT, letterSpacing: 2 }}>
          五行相生 · 生生不息
        </div>
        <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', marginTop: 18 }}>
          {elementOrder.map((elem, i) => (
            <div key={elem} style={{ display: 'flex', flexDirection: 'row', alignItems: 'center' }}>
              <ElementCircle elem={elem} active={activeElems.has(elem)} />
              {i < elementOrder.length - 1 ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 104 }}>
                  <div style={{ fontSize: 18, color: '#B5AEA0', fontFamily: FONT, marginBottom: 2 }}>生</div>
                  <div style={{ width: 88, height: 2, backgroundColor: '#B5AEA0' }} />
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </div>

      {/* 底部品牌区 */}
      <div style={{ display: 'flex', flexDirection: 'column', padding: '0 120px', marginTop: 24 }}>
        <MeanderBand width={840} />
        <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', marginTop: 20 }}>
          <Seal char="顺" size={52} fontSize={28} />
          <div style={{ display: 'flex', fontSize: 30, color: INK, marginLeft: 16, fontFamily: FONT }}>
            顺衣尚 · 五行穿搭
          </div>
          <div style={{ display: 'flex', flex: 1 }} />
          <div style={{ display: 'flex', fontSize: 22, color: INK_GRAY, fontFamily: FONT }}>
            {data.date}{data.lunar ? ` · ${data.lunar}` : ''}
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 18 }}>
          <div style={{ fontSize: 24, color: INK_GRAY, fontFamily: FONT, letterSpacing: 2 }}>
            弘扬传统文化 · 衣承五行
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 10, marginBottom: 26 }}>
          <div style={{ fontSize: 22, color: INK_GRAY, fontFamily: FONT }}>
            浏览 shunyishang.cn 领取专属五行穿搭
          </div>
        </div>
      </div>
    </div>
  )
}
