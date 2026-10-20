import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useMemo } from 'react'
import { AnimatedMoney, Money } from '@/components/Money'
import { useCurrency } from '@/context/CurrencyContext'
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
  const { currency, config } = useCurrency()
  const disputedShare =
    docket.total_billed_cents > 0 ? docket.total_disputed_cents / docket.total_billed_cents : 0

  return (
    <div className="paper rounded-2xl border border-paper-rule p-4 sm:p-8">
      <div className="grid grid-cols-1 gap-6 min-[420px]:grid-cols-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="label-mono text-paper-muted">Total billed</p>
                  {currency !== 'USD' && (
                    <span className="rounded bg-accent/40 px-1.5 py-0.5 text-[10px] font-mono text-paper-muted">
                      {currency}
                    </span>
                  )}
                </div>
                <AnimatedMoney
                  cents={docket.total_billed_cents}
                  className="mt-1 block font-mono text-3xl tracking-tight sm:text-4xl"
                />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="label-mono text-on-paper-emphasis">Total disputed</p>
                  {currency !== 'USD' && (
                    <span className="rounded bg-accent/40 px-1.5 py-0.5 text-[10px] font-mono text-on-paper-emphasis">
                      {currency}
                    </span>
                  )}
                </div>
                <AnimatedMoney
                  cents={docket.total_disputed_cents}
                  delay={0.3}
                  className="mt-1 block font-mono text-3xl tracking-tight text-on-paper-emphasis sm:text-4xl"
                />
              </div>
      </div>
      {currency !== 'USD' && (
        <p className="mt-3 font-mono text-[11px] text-paper-muted">
          Converted from USD baseline at {config.rateToUsd} {currency}/USD
        </p>
      )}
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
      <ul className="flex flex-col gap-3 md:hidden">
        {disputed.map((finding) => (
          <li
            key={finding.line_item.line_item_id}
            className="rounded-xl border-2 border-border p-4"
          >
            <p className="text-sm font-medium text-pretty">{finding.line_item.description}</p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              {finding.line_item.cpt_hcpcs_code ?? '—'}
            </p>
            <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="font-mono text-[0.65rem] tracking-wide text-muted-foreground uppercase">
                  Billed
                </dt>
                <dd className="mt-1">
                  <Money cents={finding.line_item.billed_amount_cents} />
                </dd>
              </div>
              <div>
                <dt className="font-mono text-[0.65rem] tracking-wide text-muted-foreground uppercase">
                  Disputed
                </dt>
                <dd className="mt-1 font-medium text-emphasis">
                  <Money cents={finding.disputed_amount_cents} />
                </dd>
              </div>
            </dl>
            {finding.compliance_finding?.citation ? (
              <p className="mt-3 font-mono text-xs text-muted-foreground">
                {finding.compliance_finding.citation}
              </p>
            ) : null}
          </li>
        ))}
        {disputed.length === 0 && (
          <li className="py-8 text-center text-sm text-muted-foreground">
            No disputed line items — every charge reconciled within federal limits.
          </li>
        )}
      </ul>
      <div className="hidden md:block">
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
      </div>
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
        <div className="flex flex-col gap-1 border-b border-dashed py-2 sm:flex-row sm:items-baseline sm:justify-between sm:gap-4">
          <dt className="text-muted-foreground">Certified</dt>
          <dd className="font-medium sm:text-right">
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
