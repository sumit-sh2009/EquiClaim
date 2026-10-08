import type { CSSProperties, InputHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'
import './brutalist-input.css'

export interface BrutalistInputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean
  containerClassName?: string
}

/**
 * Hard-shadow monospace input — Uiverse.io by 0xnihilism (shake/blink stripped).
 */
export function BrutalistInput({
  className,
  containerClassName,
  invalid,
  style,
  ...props
}: BrutalistInputProps) {
  return (
    <div
      className={cn('brutalist-input-container', containerClassName)}
      style={
        {
          '--brutal-bg': 'var(--paper)',
          '--brutal-ink': 'var(--paper-ink)',
          ...style,
        } as CSSProperties
      }
    >
      <input
        className={cn('brutalist-input', invalid && 'brutalist-input--invalid', className)}
        {...props}
      />
    </div>
  )
}
