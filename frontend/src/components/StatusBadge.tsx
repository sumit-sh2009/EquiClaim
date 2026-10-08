import { cn } from '@/lib/utils'
import type { ClaimStatus } from '@/types/api'

/**
 * Claim status as a small dot + label — a ledger annotation, not a pill.
 * Color is semantic: amber = needs a human, green = certified, red = failed.
 */
const STATUS_CONFIG: Record<ClaimStatus, { label: string; dot: string; text: string }> = {
  INTAKE: { label: 'Intake', dot: 'bg-muted-foreground/50', text: 'text-muted-foreground' },
  BENCHMARKING: { label: 'Benchmarking', dot: 'bg-info', text: 'text-info' },
  COMPLIANCE_REVIEW: { label: 'Compliance review', dot: 'bg-info', text: 'text-info' },
  EVALUATING: { label: 'Evaluating', dot: 'bg-info', text: 'text-info' },
  AWAITING_HUMAN_REVIEW: { label: 'Awaiting review', dot: 'bg-warning', text: 'text-warning' },
  RESUMING: { label: 'Resuming', dot: 'bg-warning', text: 'text-warning' },
  CERTIFIED: { label: 'Certified', dot: 'bg-success', text: 'text-success' },
  REJECTED: { label: 'Rejected', dot: 'bg-muted-foreground/50', text: 'text-muted-foreground' },
  FAILED: { label: 'Escalated', dot: 'bg-destructive', text: 'text-destructive' },
}

export function StatusBadge({ status, className }: { status: ClaimStatus; className?: string }) {
  const config = STATUS_CONFIG[status] ?? {
    label: status,
    dot: 'bg-muted-foreground/50',
    text: 'text-muted-foreground',
  }
  const active = !['CERTIFIED', 'REJECTED', 'FAILED'].includes(status)
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-sm font-medium', config.text, className)}>
      <span
        aria-hidden
        className={cn('size-1.5 rounded-full', config.dot, active && 'animate-pulse motion-reduce:animate-none')}
      />
      {config.label}
    </span>
  )
}
