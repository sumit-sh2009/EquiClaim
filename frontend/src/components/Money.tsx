import { cn } from '@/lib/utils'
import { NumberTicker } from '@/components/ui/number-ticker'

export function formatCents(cents: number): string {
  return (cents / 100).toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

/** Money always sets in tabular figures so columns of amounts align. */
export function Money({ cents, className }: { cents: number; className?: string }) {
  return <span className={cn('tnum', className)}>{formatCents(cents)}</span>
}

/**
 * Money that counts up when scrolled into view. Reserved for hero figures —
 * tables stay quiet. Screen readers get the settled value up front.
 */
export function AnimatedMoney({
  cents,
  className,
  delay = 0,
}: {
  cents: number
  className?: string
  delay?: number
}) {
  return (
    <span className={cn('tnum', className)} aria-label={formatCents(cents)}>
      <span aria-hidden>
        $<NumberTicker value={cents / 100} decimalPlaces={2} delay={delay} />
      </span>
    </span>
  )
}
