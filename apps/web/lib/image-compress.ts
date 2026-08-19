/**
 * 客户端图片压缩工具
 *
 * 后端 upload-image 硬性限制单张 ≤5MB，为避免用户选图被拒，
 * 上传前在浏览器端用 Canvas 渐进压缩（降质量 + 降分辨率）至限制内。
 * 仅对超限图片触发，未超限原样返回，零损耗。
 */

/** 压缩后最长边上限（衣物识别无需超高分辨率） */
const MAX_DIMENSION = 2048

/** 渐进压缩档位：质量 × 缩放 组合，从高质量向小体积尝试 */
const QUALITY_STEPS = [0.92, 0.8, 0.65, 0.5]
const SCALE_STEPS = [1, 0.75, 0.55, 0.4]

function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('图片解析失败'))
    }
    img.src = url
  })
}

function drawToBlob(
  img: HTMLImageElement,
  scale: number,
  quality: number
): Promise<Blob | null> {
  return new Promise((resolve) => {
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(img.naturalWidth * scale))
    canvas.height = Math.max(1, Math.round(img.naturalHeight * scale))
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      resolve(null)
      return
    }
    // JPEG 无透明通道，先铺白底避免透明区变黑
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    canvas.toBlob((blob) => resolve(blob), 'image/jpeg', quality)
  })
}

/**
 * 将图片文件压缩至 maxBytes 以内
 *
 * - 未超限：原样返回（不重编码，零损耗）
 * - 超限：最长边先收敛到 MAX_DIMENSION，再按 质量×缩放 档位渐进重编码，
 *   首个满足体积限制的结果即返回；全部档位仍超限则返回最小的一档
 * - 输出统一为 image/jpeg（.jpg），与后端 JPG/PNG/WebP 白名单兼容
 *
 * @returns 压缩后的 File（可能为原文件）
 */
export async function compressImageFile(file: File, maxBytes: number): Promise<File> {
  if (file.size <= maxBytes) {
    return file
  }

  const img = await loadImage(file)

  // 最长边收敛到 MAX_DIMENSION 内的初始缩放
  const longest = Math.max(img.naturalWidth, img.naturalHeight)
  const baseScale = longest > MAX_DIMENSION ? MAX_DIMENSION / longest : 1

  let smallest: Blob | null = null

  for (const scaleStep of SCALE_STEPS) {
    for (const quality of QUALITY_STEPS) {
      const blob = await drawToBlob(img, baseScale * scaleStep, quality)
      if (!blob) continue
      if (!smallest || blob.size < smallest.size) {
        smallest = blob
      }
      if (blob.size <= maxBytes) {
        return toJpegFile(file, blob)
      }
    }
  }

  // 全部档位仍超限：返回最小的一档，由调用方决定是否拒绝
  if (smallest) {
    return toJpegFile(file, smallest)
  }
  return file
}

function toJpegFile(source: File, blob: Blob): File {
  const baseName = source.name.replace(/\.[^.]+$/, '') || 'image'
  return new File([blob], `${baseName}.jpg`, { type: 'image/jpeg' })
}
