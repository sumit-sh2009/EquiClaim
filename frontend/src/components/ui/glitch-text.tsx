import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export function GlitchText({
  className,
  children,
  as: Tag = 'span',
  ...props
}: HTMLAttributes<HTMLElement> & { as?: 'span' | 'h1' | 'h2' | 'p' }) {
  return (
    <Tag className={cn('display glitch-text', className)} {...props}>
      {children}
    </Tag>
  )
}
