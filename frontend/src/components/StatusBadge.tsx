import type { ClaimStatus } from '../types/api'

const STATUS_STYLES: Record<ClaimStatus, string> = {
  INTAKE: 'bg-slate-100 text-slate-700',
  BENCHMARKING: 'bg-sky-100 text-sky-700',
  COMPLIANCE_REVIEW: 'bg-indigo-100 text-indigo-700',
  EVALUATING: 'bg-amber-100 text-amber-700',
  AWAITING_HUMAN_REVIEW: 'bg-orange-100 text-orange-800 animate-pulse',
  CERTIFIED: 'bg-emerald-100 text-emerald-800',
  REJECTED: 'bg-slate-200 text-slate-600',
  FAILED: 'bg-red-100 text-red-700',
}

export function StatusBadge({ status }: { status: ClaimStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {status.replaceAll('_', ' ')}
    </span>
  )
}
