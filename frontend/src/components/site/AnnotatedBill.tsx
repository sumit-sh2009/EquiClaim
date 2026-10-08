import {
  motion,
  useInView,
  useMotionValue,
  useReducedMotion,
  useTransform,
  type MotionValue,
} from 'motion/react'
import { useRef } from 'react'
import { Money } from '@/components/Money'
import { cn } from '@/lib/utils'

export type BillFocus = 'read' | 'price' | 'cite'

const LINES = [
  { ref: '1', description: 'Emergency department visit level 4', code: '99284', billed: '$1,500.00' },
  { ref: '2', description: 'Routine venipuncture', code: '36415', billed: '$45.00' },
  { ref: '3', description: 'Chest X-ray, 2 views', code: '71046', billed: '$180.00' },
  { ref: '4', description: 'Chest X-ray, 1 view', code: '71045', billed: '$110.00' },
] as const

function lineHot(focus: BillFocus | undefined, code: string) {
  if (!focus) return true
  if (focus === 'cite') return code === '71045' || code === '36415'
  return code === '99284'
}

function BillScan({
  progress,
  playOnce,
}: {
  progress?: MotionValue<number>
  playOnce: boolean
}) {
  const reduceMotion = useReducedMotion()
  const fallback = useMotionValue(0)
  const top = useTransform(progress ?? fallback, [0, 1], ['-18%', '100%'])
  if (reduceMotion) return null
  if (progress) {
    return (
      <motion.div
        aria-hidden
        style={{ top }}
        className="pointer-events-none absolute inset-x-0 z-20 h-16 bg-[linear-gradient(to_bottom,transparent,var(--lab-glow))] mix-blend-multiply transform-gpu"
      >
        <div className="absolute inset-x-0 bottom-0 h-px bg-lab shadow-[0_0_12px_var(--lab)]" />
      </motion.div>
    )
  }
  if (!playOnce) return null
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 z-20 overflow-hidden">
      <div className="animate-scan absolute inset-x-0 top-0 h-16 bg-[linear-gradient(to_bottom,transparent,var(--lab-glow))] mix-blend-multiply">
        <div className="absolute inset-x-0 bottom-0 h-px bg-lab shadow-[0_0_12px_var(--lab)]" />
      </div>
    </div>
  )
}

export function AnnotatedBillFigure({
  className,
  focus,
  scanProgress,
}: {
  className?: string
  focus?: BillFocus
  scanProgress?: MotionValue<number>
}) {
  const ref = useRef<HTMLElement>(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })
  const reduceMotion = useReducedMotion()
  const drawn = inView ? 'drawn' : undefined

  return (
    <figure ref={ref} className={cn('relative w-full select-none', className)}>
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-10 -z-10 rounded-[3rem] bg-[radial-gradient(60%_50%_at_50%_30%,var(--audit-glow),transparent_70%)] animate-lamp blur-2xl"
      />

      <div className="paper relative z-10 overflow-hidden rounded-[32px]">
        <BillScan progress={scanProgress} playOnce={!reduceMotion && inView && !scanProgress} />

        <div className="absolute left-6 top-0 z-20 rounded-b-xl border-x-2 border-b-2 border-[#09090B] bg-[#D2E823] px-3 py-1 lg:left-8">
          <span className="label-mono text-[0.625rem] text-accent-foreground">Exhibit A</span>
        </div>

        <div className="relative flex items-baseline justify-between gap-4 border-b border-paper-rule inset-x pb-6 pt-10">
          <div>
            <p className="label-mono text-paper-muted">Statement of services</p>
            <p className="flow-sm font-heading text-2xl font-semibold tracking-tight text-paper-ink sm:text-3xl">
              Mercy General
            </p>
          </div>
          <p className="font-mono text-xs text-paper-muted sm:text-sm">
            2026-01-15
            <span aria-hidden className="mx-2 text-paper-rule">
              /
            </span>
            POS 23
          </p>
        </div>

        <ul className="relative inset-x text-base sm:text-lg">
          {LINES.map((line) => (
            <li
              key={line.ref}
              className={cn(
                'flex items-baseline gap-4 border-b border-dashed border-paper-rule px-2 py-4 transition-opacity duration-300 last:border-0',
                focus && !lineHot(focus, line.code) && 'opacity-35',
                focus && lineHot(focus, line.code) && 'bg-accent/50',
              )}
            >
              <span className="w-5 shrink-0 font-mono text-xs text-paper-muted">{line.ref}</span>
              <span className="min-w-0 flex-1 truncate font-medium text-paper-ink">
                {line.description}
              </span>
              <span className="hidden shrink-0 font-mono text-sm text-paper-muted sm:inline">
                {line.code}
              </span>
              {line.ref === '1' ? (
                <span
                  className={cn(
                    'redline shrink-0 font-mono text-lg font-semibold text-paper-ink',
                    drawn,
                  )}
                >
                  {line.billed}
                </span>
              ) : (
                <span
                  className={cn(
                    'shrink-0 font-mono text-lg font-medium text-paper-ink',
                    line.ref === '4' && 'text-paper-muted line-through decoration-audit/80',
                  )}
                >
                  {line.billed}
                </span>
              )}
            </li>
          ))}
        </ul>

        <div className="relative flex flex-col gap-4 border-t border-paper-rule bg-audit/[0.055] inset-x py-6">
          <p
            className={cn(
              'flex gap-4 font-sans text-sm leading-relaxed text-on-paper-emphasis italic transition-opacity duration-300 sm:text-base',
              focus && !lineHot(focus, '99284') && 'opacity-30',
            )}
          >
            <span aria-hidden className="mt-2 h-px w-5 shrink-0 bg-audit/60" />
            <span>
              <span className="font-mono text-xs font-medium not-italic">99284</span> — patient
              responsibility $1,180.00 against a $320.00 median. $860.00 sits above the No Surprises
              Act cap.
            </span>
          </p>
          <p
            className={cn(
              'flex gap-4 font-sans text-sm leading-relaxed text-on-paper-emphasis italic transition-opacity duration-300 sm:text-base',
              focus && !lineHot(focus, '36415') && 'opacity-30',
            )}
          >
            <span aria-hidden className="mt-2 h-px w-5 shrink-0 bg-audit/60" />
            <span>
              <span className="font-mono text-xs font-medium not-italic">36415</span> — $37.00 of
              patient responsibility against an $8.00 median. $29.00 disputed.
            </span>
          </p>
          <p
            className={cn(
              'flex gap-4 font-sans text-sm leading-relaxed text-on-paper-emphasis italic transition-opacity duration-300 sm:text-base',
              focus && !lineHot(focus, '71045') && 'opacity-30',
            )}
          >
            <span aria-hidden className="mt-2 h-px w-5 shrink-0 bg-audit/60" />
            <span>
              <span className="font-mono text-xs font-medium not-italic">71045</span> — NCCI PTP
              edit: the single-view X-ray bundles into the two-view study. $110.00 disallowed.
            </span>
          </p>
        </div>

        <div
          data-totals
          className="relative flex items-end justify-between gap-4 border-t border-paper-rule inset-x py-6"
        >
          <div className="min-w-0">
            <p className="label-mono text-paper-muted">Total billed</p>
            <Money
              cents={183500}
              className="flow-sm block font-mono text-2xl font-medium tracking-tight text-paper-ink sm:text-3xl"
            />
          </div>
          <div
            className={cn(
              'min-w-0 rounded-xl text-right transition-colors duration-300',
              focus === 'price' && 'bg-accent/70 px-3 py-2',
            )}
          >
            <p className="label-mono text-on-paper-emphasis">Disputed</p>
            <Money
              cents={99900}
              className="flow-sm block font-mono text-3xl font-medium tracking-tight text-on-paper-emphasis sm:text-4xl"
            />
          </div>
        </div>
      </div>

      <figcaption className="flow-md flex items-start gap-4 text-sm leading-relaxed text-muted-foreground">
        <span aria-hidden className="mt-2 h-px w-8 shrink-0 bg-border" />
        <span>
          A sample statement carrying the audit&rsquo;s actual findings — CARC 45, NCCI bundling,
          and the No Surprises Act limit on patient responsibility.
        </span>
      </figcaption>
    </figure>
  )
}
