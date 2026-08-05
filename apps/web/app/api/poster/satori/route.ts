/**
 * Satori 海报出图 API Route（阶段2）
 * POST /api/poster/satori
 *
 * 与后端 Pillow /api/v1/poster/generate-base64 同构的返回：
 *   { image: base64, filename, size }
 *
 * 链路：JSX(Satori) → SVG → resvg PNG。仅支持 layout='guofeng'，
 * 其他模板/字体缺失等异常返回 503，前端自动回退 Pillow 出图。
 */
import { NextRequest, NextResponse } from 'next/server'
import satori from 'satori'
import { Resvg } from '@resvg/resvg-js'
import { promises as fs } from 'fs'
import path from 'path'
import { GuofengSatori, type SatoriPosterItem } from '@/lib/poster-satori'
import { getTodayLunar } from '@/lib/lunar'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const POSTER_W = 1080
const POSTER_H = 1920

// ---------- 字体（模块级缓存） ----------

let fontBuffer: ArrayBuffer | null = null

async function loadFont(): Promise<ArrayBuffer> {
  if (fontBuffer) return fontBuffer
  const dir = path.join(process.cwd(), 'public', 'fonts')
  for (const name of ['poster-serif.ttf', 'poster-serif.otf', 'poster-serif.woff']) {
    try {
      const buf = await fs.readFile(path.join(dir, name))
      fontBuffer = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) as ArrayBuffer
      return fontBuffer
    } catch {
      // 尝试下一个候选
    }
  }
  throw new Error('poster-serif font not found')
}

// ---------- 质感资产（宣纸纹理，模块级缓存） ----------

let paperTextureData: string | null = null

async function loadPaperTexture(): Promise<string | undefined> {
  if (paperTextureData) return paperTextureData
  // 本地开发: apps/web → 仓库根 data/ ；Docker: 构建时 COPY 到 ./poster_assets
  const candidates = [
    path.join(process.cwd(), '..', '..', 'data', 'standards', 'poster_assets', 'paper_texture.png'),
    path.join(process.cwd(), 'poster_assets', 'paper_texture.png'),
  ]
  for (const p of candidates) {
    try {
      const buf = await fs.readFile(p)
      paperTextureData = `data:image/png;base64,${buf.toString('base64')}`
      return paperTextureData
    } catch {
      // 尝试下一个候选
    }
  }
  return undefined
}

// ---------- 单品图片 → data URI ----------

const API_BASE = () => process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function fetchAsDataUri(url: string): Promise<string | undefined> {
  try {
    let abs = url
    if (url.startsWith('/')) {
      abs = `${API_BASE()}${url}`
    } else if (!/^https?:\/\//.test(url)) {
      return undefined
    }
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 4000)
    const res = await fetch(abs, { signal: controller.signal })
    clearTimeout(timer)
    if (!res.ok) return undefined
    const contentType = res.headers.get('content-type')?.split(';')[0] || 'image/png'
    const buf = Buffer.from(await res.arrayBuffer())
    return `data:${contentType};base64,${buf.toString('base64')}`
  } catch {
    return undefined
  }
}

// ---------- 主处理 ----------

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    if (body.layout && body.layout !== 'guofeng') {
      return NextResponse.json({ error: 'satori route only supports guofeng layout' }, { status: 503 })
    }

    const font = await loadFont().catch(() => null)
    if (!font) {
      return NextResponse.json({ error: 'poster font not ready' }, { status: 503 })
    }

    // 并行预取单品图片（失败降级为无图占位）
    const rawItems: Array<Record<string, unknown>> = Array.isArray(body.items) ? body.items.slice(0, 6) : []
    const imageDataList = await Promise.all(
      rawItems.map((it) => (it.image_url ? fetchAsDataUri(String(it.image_url)) : Promise.resolve(undefined)))
    )
    const items: SatoriPosterItem[] = rawItems.map((it, i) => ({
      name: String(it.name || ''),
      image_data: imageDataList[i],
      primary_element: it.primary_element ? String(it.primary_element) : undefined,
      category: it.category ? String(it.category) : undefined,
      reason: it.reason ? String(it.reason) : undefined,
    }))

    // 农历（lunar-javascript，与后端 cnlunar 口径一致）
    let lunar = ''
    try {
      const today = getTodayLunar()
      if (today) {
        lunar = `${today.yearGanZhi}年${today.lunarMonthDisplay}${today.lunarDayDisplay}`
      }
    } catch {
      lunar = ''
    }

    const now = new Date()
    const date = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`

    const svg = await satori(
      GuofengSatori({
        title: body.title || '今日五行穿搭推荐',
        items,
        xiyong_elements: Array.isArray(body.xiyong_elements) ? body.xiyong_elements : [],
        theme: body.theme || 'fire',
        quote: body.quote || '',
        username: body.username || '',
        lunar,
        date,
        paper_texture_data: await loadPaperTexture(),
      }) as any,
      {
        width: POSTER_W,
        height: POSTER_H,
        fonts: [{ name: 'PosterSerif', data: font, weight: 400, style: 'normal' }],
      }
    )

    const png = new Resvg(svg, {
      fitTo: { mode: 'width', value: POSTER_W },
      background: '#F6F3E9',
    }).render().asPng()

    const base64 = Buffer.from(png).toString('base64')
    return NextResponse.json({
      image: base64,
      filename: `${body.title || '五行穿搭海报'}.png`,
      size: png.byteLength,
    })
  } catch (error) {
    console.error('[poster/satori] 生成失败:', error)
    return NextResponse.json({ error: 'satori poster generation failed' }, { status: 503 })
  }
}
