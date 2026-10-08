import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

/**
 * Shared exhibit chrome: ink border, hard offset shadow, optional acid tab.
 * Used by the landing statement and the upload, ledger, and claim surfaces.
 */
export function ExhibitFrame({
  kicker,
  children,
  className,
  tone = 'card',
}: {
  kicker?: string
  children: ReactNode
  className?: string
  tone?: 'card' | 'ink'
}) {
  return (
    <div className="relative">
      {kicker ? (
        <p className="absolute left-6 top-0 z-10 -translate-y-1/2 rounded-full border-2 border-border bg-accent px-3 py-1 font-mono text-[0.65rem] font-medium tracking-[0.16em] text-accent-foreground uppercase">
          {kicker}
        </p>
      ) : null}
      <div
        className={cn(
          'overflow-hidden rounded-[32px] border-2 border-border shadow-[var(--hard-lg)]',
          tone === 'ink' ? 'bg-primary text-primary-foreground' : 'bg-card text-card-foreground',
          className,
        )}
      >
        {children}
      </div>
    </div>
  )
}
