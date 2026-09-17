import type { AuditDocket } from '../types/api'
import { Money } from './Money'

export function DocketViewer({ docket }: { docket: AuditDocket }) {
  const disputed = docket.line_item_findings.filter((f) => f.disputed_amount_cents > 0)

  return (
    <div className="mt-6 space-y-6">
      <div className="grid grid-cols-3 gap-4 rounded-lg border border-slate-200 bg-white p-4">
        <div>
          <div className="text-xs uppercase text-slate-500">Total billed</div>
          <Money cents={docket.total_billed_cents} className="text-lg font-semibold text-slate-900" />
        </div>
        <div>
          <div className="text-xs uppercase text-slate-500">Total disputed</div>
          <Money cents={docket.total_disputed_cents} className="text-lg font-semibold text-red-600" />
        </div>
        <div>
          <div className="text-xs uppercase text-slate-500">Evaluator iterations</div>
          <div className="text-lg font-semibold text-slate-900">
            {docket.evaluator_certification.iteration_count}
          </div>
        </div>
      </div>

      {docket.human_approval && (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
          <span className="font-medium">Human decision:</span> {docket.human_approval.decision}
          {docket.human_approval.approved_by && <> by {docket.human_approval.approved_by}</>} on{' '}
          {new Date(docket.human_approval.decided_at).toLocaleString()}
          {docket.human_approval.notes && <div className="mt-1 text-slate-500">"{docket.human_approval.notes}"</div>}
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold text-slate-900">Disputed line items</h3>
        <div className="mt-2 overflow-hidden rounded-lg border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-slate-500">Description</th>
                <th className="px-3 py-2 text-left font-medium text-slate-500">Code</th>
                <th className="px-3 py-2 text-right font-medium text-slate-500">Billed</th>
                <th className="px-3 py-2 text-right font-medium text-slate-500">Disputed</th>
                <th className="px-3 py-2 text-left font-medium text-slate-500">Citation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {disputed.map((finding) => (
                <tr key={finding.line_item.line_item_id}>
                  <td className="px-3 py-2">{finding.line_item.description}</td>
                  <td className="px-3 py-2 font-mono text-xs">{finding.line_item.cpt_hcpcs_code}</td>
                  <td className="px-3 py-2 text-right">
                    <Money cents={finding.line_item.billed_amount_cents} />
                  </td>
                  <td className="px-3 py-2 text-right font-semibold text-red-600">
                    <Money cents={finding.disputed_amount_cents} />
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-500">
                    {finding.compliance_finding?.citation ?? '—'}
                  </td>
                </tr>
              ))}
              {disputed.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-4 text-center text-slate-400">
                    No disputed line items found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-900">Statutory authorities cited</h3>
        <ul className="mt-2 list-inside list-disc text-sm text-slate-700">
          {docket.statutory_citations.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-900">Formal dispute notice</h3>
        <pre className="mt-2 whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-4 font-mono text-xs text-slate-800">
          {docket.dispute_notice_text}
        </pre>
      </div>
    </div>
  )
}
