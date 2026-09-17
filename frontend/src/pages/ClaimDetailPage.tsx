import { Link, useParams } from 'react-router-dom'
import { DocketViewer } from '../components/DocketViewer'
import { ReviewPanel } from '../components/ReviewPanel'
import { StatusBadge } from '../components/StatusBadge'
import { useClaimStatus, useDocket } from '../hooks/useClaims'

export function ClaimDetailPage() {
  const { claimId } = useParams<{ claimId: string }>()
  const { data: status, isLoading } = useClaimStatus(claimId)
  const showDocket = status?.status === 'AWAITING_HUMAN_REVIEW' || status?.status === 'CERTIFIED' || status?.status === 'REJECTED'
  const { data: docket } = useDocket(claimId, showDocket)

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <Link to="/" className="text-sm text-indigo-600 hover:underline">
        &larr; Back to ledger
      </Link>

      <div className="mt-2 flex items-center gap-3">
        <h1 className="font-mono text-lg font-semibold text-slate-900">{claimId}</h1>
        {status && <StatusBadge status={status.status} />}
      </div>

      {isLoading && <p className="mt-6 text-sm text-slate-500">Loading claim status…</p>}

      {status && (
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <Stat label="Evaluator status" value={status.eval_status ?? '—'} />
          <Stat label="Iteration" value={String(status.eval_iteration ?? 0)} />
          <Stat label="Pending node(s)" value={status.next_nodes.join(', ') || '—'} />
          <Stat label="Warnings" value={String(status.errors.length)} />
        </div>
      )}

      {status && status.eval_feedback.length > 0 && (
        <details className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
          <summary className="cursor-pointer font-medium text-slate-800">
            Evaluator feedback history ({status.eval_feedback.length})
          </summary>
          <ul className="mt-2 space-y-1">
            {status.eval_feedback.map((fb, i) => (
              <li key={i}>{fb}</li>
            ))}
          </ul>
        </details>
      )}

      {status?.status === 'AWAITING_HUMAN_REVIEW' && claimId && <ReviewPanel claimId={claimId} />}

      {status?.status === 'FAILED' && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          This claim could not be automatically certified and has been escalated for manual
          review outside the automated pipeline.
        </div>
      )}

      {docket && <DocketViewer docket={docket} />}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <div className="text-xs uppercase text-slate-500">{label}</div>
      <div className="mt-0.5 font-medium text-slate-900">{value}</div>
    </div>
  )
}
