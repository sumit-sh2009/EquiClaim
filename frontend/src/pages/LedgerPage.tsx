import { Link } from 'react-router-dom'
import { StatusBadge } from '../components/StatusBadge'
import { useClaimList } from '../hooks/useClaims'

export function LedgerPage() {
  const { data, isLoading, isError } = useClaimList()

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Claim ledger</h1>
        <Link
          to="/upload"
          className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
        >
          + New claim
        </Link>
      </div>

      {isLoading && <p className="mt-6 text-sm text-slate-500">Loading…</p>}
      {isError && <p className="mt-6 text-sm text-red-600">Failed to load claims.</p>}

      {data && data.claims.length === 0 && (
        <p className="mt-6 text-sm text-slate-500">
          No claims yet.{' '}
          <Link to="/upload" className="text-indigo-600 hover:underline">
            Submit your first claim
          </Link>
          .
        </p>
      )}

      {data && data.claims.length > 0 && (
        <div className="mt-6 overflow-hidden rounded-lg border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Claim</th>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Hospital</th>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Status</th>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {data.claims.map((claim) => (
                <tr key={claim.claim_id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm">
                    <Link
                      to={`/claims/${claim.claim_id}`}
                      className="font-mono text-xs text-indigo-600 hover:underline"
                    >
                      {claim.claim_id.slice(0, 8)}…
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-700">{claim.hospital_ccn ?? '—'}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={claim.status} />
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-500">
                    {new Date(claim.updated_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
