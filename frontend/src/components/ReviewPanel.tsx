import { useState } from 'react'
import { useResumeClaim } from '../hooks/useClaims'

export function ReviewPanel({ claimId }: { claimId: string }) {
  const resume = useResumeClaim(claimId)
  const [reviewer, setReviewer] = useState('')
  const [notes, setNotes] = useState('')

  return (
    <div className="mt-6 rounded-lg border border-orange-200 bg-orange-50 p-5">
      <h2 className="text-sm font-semibold text-orange-900">Human review required</h2>
      <p className="mt-1 text-sm text-orange-800">
        The evaluator-optimizer loop certified this docket. Review the findings below and approve
        or reject before the dispute notice is finalized and filed.
      </p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <label className="block text-xs font-medium text-orange-900">Reviewer</label>
          <input
            value={reviewer}
            onChange={(e) => setReviewer(e.target.value)}
            placeholder="you@example.com"
            className="mt-1 w-full rounded-md border border-orange-300 px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-orange-900">Notes (optional)</label>
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="mt-1 w-full rounded-md border border-orange-300 px-2 py-1.5 text-sm"
          />
        </div>
      </div>

      {resume.isError && (
        <p className="mt-3 text-sm text-red-600">{(resume.error as Error).message}</p>
      )}

      <div className="mt-4 flex gap-3">
        <button
          onClick={() => resume.mutate({ decision: 'APPROVED', reviewer, notes })}
          disabled={resume.isPending}
          className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          Approve &amp; file dispute
        </button>
        <button
          onClick={() => resume.mutate({ decision: 'REJECTED', reviewer, notes })}
          disabled={resume.isPending}
          className="rounded-md bg-white px-4 py-2 text-sm font-semibold text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 disabled:opacity-50"
        >
          Reject
        </button>
      </div>
    </div>
  )
}
