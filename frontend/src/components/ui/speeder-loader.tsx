import type { CSSProperties, HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'
import './speeder-loader.css'

export interface SpeederLoaderProps extends HTMLAttributes<HTMLDivElement> {
  label?: string
}

/**
 * Wobbling speeder with streak lines — Uiverse.io by anand_4957.
 */
export function SpeederLoader({
  className,
  label = 'Loading',
  style,
  ...props
}: SpeederLoaderProps) {
  return (
    <div
      className={cn('speeder-loader-root', className)}
      role="status"
      aria-live="polite"
      aria-label={label}
      style={style as CSSProperties}
      {...props}
    >
      <div className="speeder-loader" aria-hidden>
        <span>
          <span />
          <span />
          <span />
          <span />
        </span>
        <div className="speeder-base">
          <span />
          <div className="speeder-face" />
        </div>
      </div>
      <div className="speeder-longfazers" aria-hidden>
        <span />
        <span />
        <span />
        <span />
      </div>
    </div>
  )
}
