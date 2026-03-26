'use client'

import { useEffect, useState } from 'react'

interface TypewriterTextProps {
  text: string
  speed?: number
  onComplete?: () => void
}

export function TypewriterText({ text, speed = 20, onComplete }: TypewriterTextProps) {
  const [displayText, setDisplayText] = useState('')

  useEffect(() => {
    if (!text) return

    let index = 0
    const timer = setInterval(() => {
      if (index < text.length) {
        setDisplayText(text.slice(0, index + 1))
        index++
      } else {
        clearInterval(timer)
        onComplete?.()
      }
    }, speed)

    return () => clearInterval(timer)
  }, [text, speed, onComplete])

  // 如果文本变化很大，直接显示（流式场景）
  useEffect(() => {
    if (text.length > displayText.length + 10) {
      setDisplayText(text)
    }
  }, [text])

  return <span>{displayText}</span>
}
