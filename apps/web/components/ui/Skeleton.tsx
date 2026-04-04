import { cn } from '@/lib/utils'

interface SkeletonProps {
  className?: string
  variant?: 'rectangular' | 'circular' | 'text'
  animation?: 'pulse' | 'wave' | 'none'
}

export function Skeleton({ 
  className, 
  variant = 'rectangular',
  animation = 'pulse'
}: SkeletonProps) {
  return (
    <div
      className={cn(
        'bg-[#F0F7F4] rounded-lg',
        variant === 'circular' && 'rounded-full',
        variant === 'text' && 'h-4 rounded',
        animation === 'pulse' && 'animate-pulse',
        animation === 'wave' && 'relative overflow-hidden bg-gradient-to-r from-[#F0F7F4] via-[#E8F5EC] to-[#F0F7F4] bg-[length:200%_100%] animate-[wave_1.5s_ease-in-out_infinite]',
        className
      )}
    />
  )
}

interface SkeletonCardProps {
  lines?: number
  showImage?: boolean
  className?: string
}

export function SkeletonCard({ lines = 2, showImage = true, className }: SkeletonCardProps) {
  return (
    <div className={cn('bg-white/80 rounded-xl p-4 border border-[#E8F0EB]/60 space-y-3', className)}>
      {showImage && (
        <Skeleton className="h-40 w-full" animation="wave" />
      )}
      <Skeleton className="h-4 w-3/4" />
      {lines > 1 && <Skeleton className="h-3 w-1/2" />}
      {lines > 2 && <Skeleton className="h-3 w-2/3" />}
    </div>
  )
}

interface SkeletonListProps {
  count?: number
  showImage?: boolean
  className?: string
}

export function SkeletonList({ count = 4, showImage = true, className }: SkeletonListProps) {
  return (
    <div className={cn('grid gap-4', className)}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} showImage={showImage} />
      ))}
    </div>
  )
}

// 添加 CSS 动画
if (typeof document !== 'undefined') {
  const style = document.createElement('style')
  style.textContent = `
    @keyframes wave {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  `
  if (!document.querySelector('[data-wave-animation]')) {
    style.setAttribute('data-wave-animation', 'true')
    document.head.appendChild(style)
  }
}
