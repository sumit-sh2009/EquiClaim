import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useMemo } from 'react'
import { AnimatedMoney, Money } from '@/components/Money'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { AuditDocket, LineItemFinding } from '@/types/api'

/**
 * The docket is the product's deliverable, so it's rendered like a document:
 * hard ink borders, tabular figures, and mono for citations and money.
 */

export function DocketSummary({ docket }: { docket: AuditDocket }) {
  const disputedShare =
    docket.total_billed_cents > 0 ? docket.total_disputed_cents / docket.total_billed_cents : 0

  return (
    <div className="paper rounded-2xl border border-paper-rule p-6 sm:p-8">
      <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="label-mono text-paper-muted">Total billed</p>
                <AnimatedMoney
                  cents={docket.total_billed_cents}
                  className="mt-1 block font-mono text-4xl tracking-tight"
                />
              </div>
              <div>
                <p className="label-mono text-on-paper-emphasis">Total disputed</p>
                <AnimatedMoney
                  cents={docket.total_disputed_cents}
                  delay={0.3}
                  className="mt-1 block font-mono text-4xl tracking-tight text-on-paper-emphasis"
                />
              </div>
      </div>
      {/* Disputed share — the one number that sizes the fight */}
      <div
        className="mt-5"
        role="img"
        aria-label={`${(disputedShare * 100).toFixed(0)} percent of the billed total is disputed`}
      >
        <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-paper-rule">
          <div
            className="bg-audit transition-[width] duration-500"
            style={{ width: `${Math.max(disputedShare * 100, disputedShare > 0 ? 1.5 : 0)}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-paper-muted">
          <span className="tnum font-medium text-paper-ink">
            {(disputedShare * 100).toFixed(0)}%
          </span>{' '}
          of the billed total is contested
        </p>
      </div>
    </div>
  )
}

const findingHelper = createColumnHelper<LineItemFinding>()

const findingColumns = [
  findingHelper.accessor((row) => row.line_item.description, {
    id: 'description',
    header: 'Line item',
    cell: (info) => (
      <span className="block truncate" title={info.getValue()}>
        {info.getValue()}
      </span>
    ),
  }),
  findingHelper.accessor((row) => row.line_item.cpt_hcpcs_code, {
    id: 'code',
    header: 'Code',
    cell: (info) => (
      <span className="font-mono text-sm text-muted-foreground">{info.getValue() ?? '—'}</span>
    ),
  }),
  findingHelper.accessor((row) => row.line_item.billed_amount_cents, {
    id: 'billed',
    header: 'Billed',
    cell: (info) => <Money cents={info.getValue()} />,
  }),
  findingHelper.accessor((row) => row.disputed_amount_cents, {
    id: 'disputed',
    header: 'Disputed',
    cell: (info) => (
      <span className="font-medium text-emphasis">
        <Money cents={info.getValue()} />
      </span>
    ),
  }),
  findingHelper.accessor((row) => row.compliance_finding?.citation, {
    id: 'citation',
    header: 'Authority',
    cell: (info) => (
      <span className="font-mono text-xs text-muted-foreground">{info.getValue() ?? '—'}</span>
    ),
  }),
]

export function DocketFindings({ docket }: { docket: AuditDocket }) {
  const disputed = useMemo(
    () => docket.line_item_findings.filter((f) => f.disputed_amount_cents > 0),
    [docket.line_item_findings],
  )

  const table = useReactTable({
    data: disputed,
    columns: findingColumns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => row.line_item.line_item_id,
  })

  return (
    <div>
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id} className="hover:bg-transparent">
              {headerGroup.headers.map((header) => (
                <TableHead
                  key={header.id}
                  className={`${header.column.id === 'billed' || header.column.id === 'disputed' ? 'text-right' : ''} font-mono text-xs font-normal tracking-wide text-muted-foreground`}
                >
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <TableRow key={row.id} className="hover:bg-transparent">
              {row.getVisibleCells().map((cell) => (
                <TableCell
                  key={cell.id}
                  className={
                    cell.column.id === 'description'
                      ? 'max-w-64'
                      : cell.column.id === 'billed' || cell.column.id === 'disputed'
                        ? 'text-right'
                        : undefined
                  }
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
          {disputed.length === 0 && (
            <TableRow className="hover:bg-transparent">
              <TableCell colSpan={findingColumns.length} className="py-10 text-center text-muted-foreground">
                No disputed line items — every charge reconciled within federal limits.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      {docket.statutory_citations.length > 0 && (
        <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
          <span className="font-medium text-foreground">Authorities cited:</span>{' '}
          <span className="font-mono">{docket.statutory_citations.join(' · ')}</span>
        </p>
      )}
    </div>
  )
}

export function DocketNotice({ docket }: { docket: AuditDocket }) {
  return (
    <div className="paper overflow-hidden rounded-2xl border border-paper-rule">
      <div className="border-b border-paper-rule px-6 py-3">
        <p className="label-mono text-paper-muted">Formal dispute notice</p>
      </div>
      <pre className="max-h-[36rem] overflow-auto whitespace-pre-wrap px-6 py-5 font-sans text-sm leading-relaxed text-paper-ink">
        {docket.dispute_notice_text}
      </pre>
    </div>
  )
}

export function CertificationTrail({ docket }: { docket: AuditDocket }) {
  return (
    <div className="text-sm">
      <dl className="grid gap-x-8 gap-y-2 sm:grid-cols-2">
        <div className="flex justify-between gap-4 border-b border-dashed py-2">
          <dt className="text-muted-foreground">Evaluator iterations</dt>
          <dd className="tnum font-medium">{docket.evaluator_certification.iteration_count}</dd>
        </div>
        <div className="flex justify-between gap-4 border-b border-dashed py-2">
          <dt className="text-muted-foreground">Certified</dt>
          <dd className="font-medium">
            {new Date(docket.evaluator_certification.certified_at).toLocaleString()}
          </dd>
        </div>
      </dl>

      <p className="label-mono mt-6 mb-2 text-muted-foreground">Invariants verified</p>
      <ul className="grid gap-x-8 sm:grid-cols-2">
        {docket.evaluator_certification.passed_checks.map((check) => (
          <li
            key={check}
            className="flex items-baseline gap-2 border-b border-dashed py-2 font-mono text-xs text-muted-foreground"
          >
            <span aria-hidden className="text-emphasis">
              ✓
            </span>
            {check}
          </li>
        ))}
      </ul>

      {docket.human_approval && (
        <p className="mt-6 border-t pt-4 text-muted-foreground">
          <span className="font-medium text-foreground">{docket.human_approval.decision}</span>
          {docket.human_approval.approved_by && <> by {docket.human_approval.approved_by}</>} on{' '}
          {new Date(docket.human_approval.decided_at).toLocaleString()}.
          {docket.human_approval.notes && (
            <span className="mt-1 block font-sans italic">
              &ldquo;{docket.human_approval.notes}&rdquo;
            </span>
          )}
        </p>
      )}
    </div>
  )
}
