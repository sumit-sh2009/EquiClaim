import { FileSearch, Search } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table'
import { StatusBadge } from '@/components/StatusBadge'
import { useClaimList } from '@/hooks/useClaims'
import { Button } from '@/components/ui/button'
import { ExhibitFrame } from '@/components/site/ExhibitFrame'
import { HardShadowButton } from '@/components/ui/hard-shadow-button'
import { TextReveal } from '@/components/ui/text-reveal'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { Input } from '@/components/ui/input'
import { SpeederLoader } from '@/components/ui/speeder-loader'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { ClaimListItem } from '@/types/api'

const MotionTableRow = motion.create(TableRow)

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return new Date(iso).toLocaleDateString()
}

const columnHelper = createColumnHelper<ClaimListItem>()

const columns = [
  columnHelper.accessor('claim_id', {
    header: 'Claim',
    cell: (info) => {
      const id = info.getValue()
      return (
        <Link
          to={`/claims/${id}`}
          className="font-mono text-sm text-foreground underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-ring"
          aria-label={`Open claim ${id}`}
        >
          {id.slice(0, 8)}
        </Link>
      )
    },
  }),
  columnHelper.accessor('hospital_ccn', {
    header: 'Hospital CCN',
    cell: (info) => (
      <span className="font-mono text-sm text-muted-foreground">{info.getValue() ?? '—'}</span>
    ),
  }),
  columnHelper.accessor('status', {
    header: 'Status',
    enableSorting: false,
    cell: (info) => <StatusBadge status={info.getValue()} />,
  }),
  columnHelper.accessor('updated_at', {
    header: 'Updated',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">{relativeTime(info.getValue())}</span>
    ),
  }),
]

export function LedgerPage() {
  const { data, isLoading, isError, error, refetch } = useClaimList()
  const [globalFilter, setGlobalFilter] = useState('')
  const [sorting, setSorting] = useState<SortingState>([{ id: 'updated_at', desc: true }])
  const reduceMotion = useReducedMotion()

  const claims = data?.claims ?? []

  const table = useReactTable({
    data: claims,
    columns,
    state: { globalFilter, sorting },
    onGlobalFilterChange: setGlobalFilter,
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    globalFilterFn: (row, _columnId, filterValue) => {
      const q = String(filterValue).trim().toLowerCase()
      if (!q) return true
      const claim = row.original
      return (
        claim.claim_id.toLowerCase().includes(q) ||
        (claim.hospital_ccn ?? '').toLowerCase().includes(q) ||
        claim.status.toLowerCase().replaceAll('_', ' ').includes(q)
      )
    },
  })

  const rows = table.getRowModel().rows
  const query = globalFilter.trim()

  const headerAlign = useMemo(
    () =>
      ({
        claim_id: 'text-left',
        hospital_ccn: 'text-left',
        status: 'text-left',
        updated_at: 'text-right',
      }) as Record<string, string>,
    [],
  )

  return (
    <div className="site-container section-pad max-w-6xl">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <TextReveal as="h1" play="mount" text="Ledger" className="font-heading text-4xl tracking-tighter" />
          <p className="flow-sm max-w-md text-sm leading-relaxed text-muted-foreground">
            Every audit in flight. The list polls live; rows update as claims move through the
            pipeline.
          </p>
        </div>
        <HardShadowButton to="/upload" className="px-4 py-2 text-xs">
          New audit
        </HardShadowButton>
      </div>

      <div className="flow-lg flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground" aria-live="polite">
          {data ? (
            <>
              <span className="tnum font-medium text-foreground">{rows.length}</span>
              {query ? ` of ${claims.length}` : ''} {rows.length === 1 ? 'claim' : 'claims'}
            </>
          ) : isError ? null : (
            'Loading…'
          )}
        </p>
        <div className="relative w-full sm:max-w-72">
          <Search
            className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Filter by ID, hospital, status…"
            aria-label="Filter claims"
            className="bg-card pl-8"
          />
        </div>
      </div>

      <ExhibitFrame kicker="Index" className="flow-sm px-4 py-6 sm:px-6">
        {isLoading && <SpeederLoader label="Loading claims" className="py-12" />}

        {isError && (
          <div role="alert" className="border-t py-12 text-center">
            <p className="font-medium">The ledger couldn&rsquo;t be loaded</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {(error as Error).message.includes('401')
                ? 'Your session credentials were rejected.'
                : 'The audit service may be unreachable.'}
            </p>
            <Button variant="outline" className="mt-4" onClick={() => refetch()}>
              Try again
            </Button>
          </div>
        )}

        {!isLoading && !isError && rows.length === 0 && (
          <Empty className="border-t py-16">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <FileSearch aria-hidden />
              </EmptyMedia>
              <EmptyTitle className="font-heading text-xl tracking-tighter">
                {query ? 'Nothing matches that filter' : 'No audits yet'}
              </EmptyTitle>
              <EmptyDescription className="max-w-sm">
                {query
                  ? 'Try a different claim ID, hospital CCN, or status.'
                  : 'The ledger fills in once you upload a bill and EOB for your first audit.'}
              </EmptyDescription>
            </EmptyHeader>
            {!query && (
              <EmptyContent className="flex flex-wrap gap-3 justify-center">
                <HardShadowButton to="/upload" className="px-4 py-2 text-xs">
                  Start an audit
                </HardShadowButton>
              </EmptyContent>
            )}
          </Empty>
        )}

        {rows.length > 0 && (
          <div className="overflow-hidden">
            <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id} className="hover:bg-transparent">
                  {headerGroup.headers.map((header) => {
                    const sortable = header.column.getCanSort()
                    const sorted = header.column.getIsSorted()
                    return (
                      <TableHead
                        key={header.id}
                        className={`${headerAlign[header.column.id] ?? 'text-left'} font-mono text-xs font-normal tracking-wide text-muted-foreground`}
                      >
                        {header.isPlaceholder ? null : sortable ? (
                          <button
                            type="button"
                            className="inline-flex items-center gap-1 hover:text-foreground"
                            onClick={header.column.getToggleSortingHandler()}
                          >
                            {flexRender(header.column.columnDef.header, header.getContext())}
                            <span className="tnum text-[10px]" aria-hidden>
                              {sorted === 'asc' ? '↑' : sorted === 'desc' ? '↓' : ''}
                            </span>
                          </button>
                        ) : (
                          flexRender(header.column.columnDef.header, header.getContext())
                        )}
                      </TableHead>
                    )
                  })}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {rows.map((row, i) => (
                <MotionTableRow
                  key={row.id}
                  className="group"
                  initial={reduceMotion ? false : { opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{
                    duration: 0.25,
                    delay: Math.min(i * 0.04, 0.4),
                    ease: [0.2, 0.6, 0.2, 1],
                  }}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell
                      key={cell.id}
                      className={cell.column.id === 'updated_at' ? 'text-right' : undefined}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </MotionTableRow>
              ))}
            </TableBody>
            </Table>
          </div>
        )}
      </ExhibitFrame>
    </div>
  )
}
