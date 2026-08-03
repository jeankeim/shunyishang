import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePoster } from '@/hooks/usePoster'

vi.mock('@/lib/poster-api', () => ({
  generateAndDownloadPoster: vi.fn(),
  sharePosterWithBase64: vi.fn(),
}))

vi.mock('@/lib/poster-templates', () => ({
  DEFAULT_TEMPLATE: { id: 'simple', name: 'Simple' },
  DEFAULT_THEME: { name: 'Fire', colors: {} },
}))

import { generateAndDownloadPoster, sharePosterWithBase64 } from '@/lib/poster-api'

describe('usePoster', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should initialize with default values', () => {
    const { result } = renderHook(() => usePoster())

    expect(result.current.title).toBe('今日五行穿搭推荐')
    expect(result.current.quote).toBe('')
    expect(result.current.signature).toBe('我的个人穿搭')
    expect(result.current.isGenerating).toBe(false)
    expect(result.current.error).toBeNull()
    expect(result.current.items).toEqual([])
    expect(result.current.xiyongElements).toEqual([])
    expect(result.current.scene).toBe('')
  })

  it('should initialize with custom options', () => {
    const { result } = renderHook(() => usePoster({
      initialTitle: 'Custom Title',
      initialQuote: 'Custom Quote',
      initialSignature: 'Custom Signature',
      items: [{ name: 'T-shirt', primary_element: '木' }],
      xiyongElements: ['木', '火'],
      scene: 'office',
    }))

    expect(result.current.title).toBe('Custom Title')
    expect(result.current.quote).toBe('Custom Quote')
    expect(result.current.signature).toBe('Custom Signature')
    expect(result.current.items).toEqual([{ name: 'T-shirt', primary_element: '木' }])
    expect(result.current.xiyongElements).toEqual(['木', '火'])
    expect(result.current.scene).toBe('office')
  })

  it('should update title via setTitle', () => {
    const { result } = renderHook(() => usePoster())

    act(() => {
      result.current.setTitle('New Title')
    })

    expect(result.current.title).toBe('New Title')
  })

  it('should update quote via setQuote', () => {
    const { result } = renderHook(() => usePoster())

    act(() => {
      result.current.setQuote('New Quote')
    })

    expect(result.current.quote).toBe('New Quote')
  })

  it('should update signature via setSignature', () => {
    const { result } = renderHook(() => usePoster())

    act(() => {
      result.current.setSignature('New Sig')
    })

    expect(result.current.signature).toBe('New Sig')
  })

  it('should update selectedTemplate via setSelectedTemplate', () => {
    const { result } = renderHook(() => usePoster())

    act(() => {
      result.current.setSelectedTemplate('card')
    })

    expect(result.current.selectedTemplate).toBe('card')
  })

  it('should update selectedTheme via setSelectedTheme', () => {
    const { result } = renderHook(() => usePoster())
    const newTheme = { name: 'Water', colors: {} }

    act(() => {
      result.current.setSelectedTheme(newTheme as any)
    })

    expect(result.current.selectedTheme).toEqual(newTheme)
  })

  it('should download poster successfully', async () => {
    vi.mocked(generateAndDownloadPoster).mockResolvedValue(undefined)
    const { result } = renderHook(() => usePoster({
      items: [{ name: 'T-shirt', primary_element: '木' }],
      xiyongElements: ['木'],
      scene: 'office',
    }))

    await act(async () => {
      await result.current.download()
    })

    expect(generateAndDownloadPoster).toHaveBeenCalled()
    expect(result.current.isGenerating).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('should set error on download failure', async () => {
    vi.mocked(generateAndDownloadPoster).mockRejectedValue(new Error('Download failed'))
    const { result } = renderHook(() => usePoster())

    await act(async () => {
      await result.current.download()
    })

    expect(result.current.error).toBe('Download failed')
    expect(result.current.isGenerating).toBe(false)
  })

  it('should set generic error on download non-Error failure', async () => {
    vi.mocked(generateAndDownloadPoster).mockRejectedValue('fail')
    const { result } = renderHook(() => usePoster())

    await act(async () => {
      await result.current.download()
    })

    expect(result.current.error).toBe('海报下载失败')
  })

  it('should share poster successfully', async () => {
    vi.mocked(sharePosterWithBase64).mockResolvedValue(undefined)
    const { result } = renderHook(() => usePoster({
      items: [{ name: 'T-shirt' }],
      xiyongElements: ['木'],
    }))

    await act(async () => {
      await result.current.share()
    })

    expect(sharePosterWithBase64).toHaveBeenCalled()
    expect(result.current.isGenerating).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('should set error on share failure', async () => {
    vi.mocked(sharePosterWithBase64).mockRejectedValue(new Error('Share failed'))
    const { result } = renderHook(() => usePoster())

    await act(async () => {
      await result.current.share()
    })

    expect(result.current.error).toBe('Share failed')
    expect(result.current.isGenerating).toBe(false)
  })

  it('should reset to initial values', () => {
    const { result } = renderHook(() => usePoster({
      initialTitle: 'Initial',
      initialQuote: 'InitialQuote',
      initialSignature: 'InitialSig',
    }))

    act(() => {
      result.current.setTitle('Changed')
      result.current.setQuote('Changed')
      result.current.setSignature('Changed')
    })

    act(() => {
      result.current.reset()
    })

    expect(result.current.title).toBe('Initial')
    expect(result.current.quote).toBe('InitialQuote')
    expect(result.current.signature).toBe('InitialSig')
    expect(result.current.error).toBeNull()
  })

  it('should provide posterRef', () => {
    const { result } = renderHook(() => usePoster())
    expect(result.current.posterRef).toBeDefined()
    expect(result.current.posterRef.current).toBeNull()
  })
})
