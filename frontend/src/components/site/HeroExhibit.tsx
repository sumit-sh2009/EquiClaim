import { ArrowRight } from 'lucide-react'
import { AnnotatedBillFigure } from '@/components/site/AnnotatedBill'
import { ExhibitFrame } from '@/components/site/ExhibitFrame'
import { HardShadowButton } from '@/components/ui/hard-shadow-button'
import { TextReveal } from '@/components/ui/text-reveal'

const BEATS = [
  {
    id: 'read' as const,
    n: '01',
    title: 'Read the line',
    code: '99284',
    body: 'Emergency department visit, level 4. Billed $1,500.00. This is the line the audit opens on.',
  },
  {
    id: 'price' as const,
    n: '02',
    title: 'Price it',
    code: '99284',
    body: 'Patient responsibility $1,180.00 against a $320.00 median. $860.00 sits above the No Surprises Act cap.',
  },
  {
    id: 'cite' as const,
    n: '03',
    title: 'Cite the rest',
    code: '71045',
    body: 'The single-view X-ray bundles into 71046. $110.00 disallowed. Venipuncture 36415 adds $29.00. The two-view study stands at $180.00.',
  },
]

function BeatCopy({
  beat,
  className,
}: {
  beat: (typeof BEATS)[number]
  className?: string
}) {
  return (
    <article className={className}>
      <p className="font-mono text-xs tracking-[0.18em] text-foreground">
        <span className="text-foreground">{beat.n}</span>
        <span className="mx-2 text-muted-foreground">/</span>
        <span className="text-foreground">{beat.code}</span>
      </p>
      <h2 className="mt-3 font-heading text-3xl tracking-tighter text-foreground sm:text-4xl">
        {beat.title}
      </h2>
      <p className="mt-3 max-w-md text-base leading-relaxed font-medium text-foreground/80">
        {beat.body}
      </p>
    </article>
  )
}

export function HeroExhibit() {
  return (
    <section className="relative">
      <div className="site-container section-pad-hero">
        <div className="grid w-full min-w-0 items-center gap-10 lg:grid-cols-12 lg:gap-12">
          <div className="min-w-0 lg:col-span-7">
            <span className="inline-block rotate-[-2deg] rounded-full border-2 border-border bg-accent px-4 py-1 font-heading text-xs tracking-tighter text-accent-foreground shadow-[var(--hard)]">
              Forensic audit
            </span>
            <TextReveal
              as="h1"
              play="mount"
              text={'Put the\nbill on\ntrial.'}
              className="display glitch-text mt-6 text-[clamp(2.75rem,7vw,7.5rem)] text-foreground"
            />
            <p className="mt-8 max-w-xl text-lg leading-relaxed font-medium text-foreground/80">
              EquiClaim reads the itemized bill and the EOB, prices every line against the
              hospital’s own published rates, and prepares a dispute docket a human certifies
              before anything is filed.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <HardShadowButton to="/upload" className="min-h-[3.75rem]">
                Start an audit
                <ArrowRight aria-hidden />
              </HardShadowButton>
              <HardShadowButton to="/claims" tone="paper" className="min-h-[3.75rem]">
                View the ledger
              </HardShadowButton>
            </div>

            <ol className="mt-10 flex flex-col gap-8">
              {BEATS.map((beat) => (
                <li key={beat.id}>
                  <BeatCopy beat={beat} />
                </li>
              ))}
            </ol>
          </div>

          <div className="min-w-0 lg:col-span-5">
            <ExhibitFrame className="[&_figcaption]:hidden [&_.paper]:rounded-none [&_.paper]:border-0 [&_.paper]:shadow-none">
              <AnnotatedBillFigure />
            </ExhibitFrame>
          </div>
        </div>
      </div>
    </section>
  )
}
