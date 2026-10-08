import { motion, useReducedMotion, useScroll, useTransform } from 'motion/react'
import { useRef } from 'react'
import docketDesk from '@/assets/docket-desk.jpg'
import ledgerStack from '@/assets/ledger-stack.jpg'
import lineMarkup from '@/assets/line-markup.jpg'
import { HeroExhibit } from '@/components/site/HeroExhibit'
import { HardShadowButton } from '@/components/ui/hard-shadow-button'
import { Marquee } from '@/components/ui/marquee'
import { Reveal, TextReveal } from '@/components/ui/text-reveal'
import { cn } from '@/lib/utils'

const PIPELINE_STEPS = [
  {
    n: '01',
    title: 'Read the paperwork',
    body: 'Bill and EOB parsed into cents-exact line items — CPT/HCPCS, units, adjustments.',
  },
  {
    n: '02',
    title: 'Price the hospital file',
    body: 'Each line against gross charge, cash price, and median negotiated rate.',
  },
  {
    n: '03',
    title: 'Check federal law',
    body: 'No Surprises Act and NCCI unbundling edits, with citations — never vibes.',
  },
  {
    n: '04',
    title: 'A human signs',
    body: 'The pipeline pauses. A reviewer certifies or rejects before anything is filed.',
  },
] as const

const CHECKS = [
  {
    rule: 'Balance-billing ban',
    citation: '45 CFR § 149.120',
    body: 'Out-of-network emergency services may not bill beyond in-network cost sharing.',
    dark: true,
  },
  {
    rule: 'QPA',
    citation: '45 CFR § 149.410',
    body: 'Patient responsibility vs. the plan’s median contracted rate — not the chargemaster.',
    dark: false,
  },
  {
    rule: 'Unbundling',
    citation: 'NCCI PTP',
    body: 'Component codes billed beside their comprehensive code get caught.',
    dark: false,
  },
  {
    rule: 'Price Transparency',
    citation: '45 CFR § 180.50',
    body: 'Hospital standard charges cross-checked against published discounted cash and median payer rates.',
    dark: false,
  },
] as const

const RULEBOOK = [
  { cite: '§ 149.110', name: 'Federal law controls' },
  { cite: '§ 149.120', name: 'Emergency balance billing' },
  { cite: '§ 149.130', name: 'Facility balance billing' },
  { cite: '§ 149.140', name: 'Air ambulance' },
  { cite: '§ 149.410', name: 'Qualifying payment amount' },
  { cite: '§ 180.50', name: 'Published hospital prices' },
  { cite: 'NCCI PTP', name: 'Unbundled procedures' },
] as const

const STRIP = [
  { k: '01', text: 'Every figure is a citation' },
  { k: '02', text: 'Priced from the hospital’s own file' },
  { k: '03', text: 'Nothing is filed until a person signs' },
] as const

const STORY = {
  kicker: 'The approach',
  title: 'A bill is a document.\nTreat it like one.',
  body: 'EquiClaim reads the itemized statement and the explanation of benefits, then sets each line against the prices that hospital already published. The result is a docket: what was billed, what is disputed, and the rule that says so.',
  aside: 'Built for desks that need a record, not a hunch.',
} as const

const SHOWCASE = [
  {
    code: '99284',
    title: 'Level-4 emergency visit',
    detail: 'Billed $1,500.00 · Disputed $860.00 against a $320.00 median.',
  },
  {
    code: '71045',
    title: 'Single-view chest X-ray',
    detail: 'Bundled into the two-view study. $110.00 disallowed.',
  },
  {
    code: '36415',
    title: 'Routine venipuncture',
    detail: 'Billed $45.00 · Disputed $29.00 against an $8.00 median.',
  },
] as const

const NOTES = [
  {
    quote: 'The line finally sits next to the rule that limits it.',
    by: 'Sample note',
    role: 'Billing desk',
  },
  {
    quote: 'We stopped arguing the chargemaster and started reading the published file.',
    by: 'Sample note',
    role: 'Reviewer',
  },
  {
    quote: 'The pause before filing is the part that makes the rest usable.',
    by: 'Sample note',
    role: 'Counsel',
  },
] as const

const SECURITY = [
  {
    k: '01',
    title: 'Keys',
    body: 'A tenant key is stored as a peppered HMAC-SHA256, not the key itself. The shipped secret and pepper are refused outside development and test.',
  },
  {
    k: '02',
    title: 'Tenants',
    body: 'A request for another tenant’s claim returns 404. The claim id is not confirmed.',
  },
  {
    k: '03',
    title: 'Uploads',
    body: 'A bill must be .json or .txt, and it is size-capped. A path in the filename cannot leave the claim folder.',
  },
  {
    k: '04',
    title: 'Money',
    body: 'Amounts are integer cents. A docket is certified only after a person approves it.',
  },
  {
    k: '05',
    title: 'Browser',
    body: 'The site tells the browser not to frame the page, and to load scripts, styles, and fonts only from this origin.',
  },
] as const

function ExhibitPhoto({
  src,
  alt,
  width,
  height,
  className,
}: {
  src: string
  alt: string
  width: number
  height: number
  className?: string
}) {
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      className={cn('relative overflow-hidden', className)}
      initial={reduceMotion ? false : { clipPath: 'inset(0 0 100% 0)' }}
      whileInView={reduceMotion ? undefined : { clipPath: 'inset(0 0 0% 0)' }}
      viewport={{ once: true, amount: 0.4 }}
      transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
    >
      <img
        src={src}
        alt={alt}
        width={width}
        height={height}
        loading="lazy"
        decoding="async"
        className="absolute inset-0 h-full w-full object-cover"
      />
    </motion.div>
  )
}

function AuditTrail() {
  const ref = useRef<HTMLOListElement>(null)
  const reduceMotion = useReducedMotion()
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start 0.85', 'end 0.55'],
  })
  const scaleY = useTransform(scrollYProgress, [0, 1], [0.12, 1])

  return (
    <ol ref={ref} className="relative mt-14 max-w-3xl">
      <div aria-hidden className="absolute bottom-8 left-5 top-5 w-0.5 -translate-x-1/2 bg-border" />
      <motion.div
        aria-hidden
        style={reduceMotion ? undefined : { scaleY }}
        className="absolute bottom-8 left-5 top-5 w-0.5 origin-top -translate-x-1/2 bg-accent transform-gpu"
      />
      {PIPELINE_STEPS.map((step, index) => (
        <li key={step.n} className="relative flex gap-6 pb-12 last:pb-0">
          <span className="relative z-10 flex size-10 shrink-0 items-center justify-center rounded-full border-2 border-border bg-background font-heading text-sm text-foreground">
            {step.n}
          </span>
          <Reveal delay={index * 0.06} className="pt-1">
            <h3 className="font-heading text-2xl tracking-tighter text-foreground">{step.title}</h3>
            <p className="mt-2 max-w-xl text-sm leading-relaxed font-medium text-muted-foreground">
              {step.body}
            </p>
          </Reveal>
        </li>
      ))}
    </ol>
  )
}

export function LandingPage() {
  const ruling = CHECKS[0]
  const notes = CHECKS.slice(1)

  return (
    <div className="flex flex-col">
      <HeroExhibit />

      <section aria-label="Why the docket holds" className="border-y-2 border-border">
        <ul className="site-container grid gap-4 py-8 sm:grid-cols-3 lg:py-10">
          {STRIP.map((item) => (
            <li key={item.k}>
              <article className="flex h-full min-h-44 flex-col justify-between rounded-xl border-2 border-border bg-card p-6 text-card-foreground shadow-[var(--hard)] transition-transform duration-150 hover:translate-x-1 hover:translate-y-1 hover:shadow-none">
                <span className="font-heading text-4xl tracking-tighter text-emphasis">{item.k}</span>
                <p className="mt-8 font-heading text-2xl leading-tight tracking-tighter text-foreground">
                  {item.text}
                </p>
              </article>
            </li>
          ))}
        </ul>
      </section>

      <section
        aria-label="Authorities the audit can cite"
        className="overflow-hidden border-b-2 border-border bg-accent text-accent-foreground"
      >
        <div className="site-container pt-8 pb-4">
          <p className="font-heading text-3xl tracking-tighter uppercase">Authorities</p>
        </div>
        <Marquee pauseOnHover className="pb-8 [--duration:45s] [--gap:1rem]">
          {RULEBOOK.map((item) => (
            <article
              key={item.cite}
              className="flex h-40 w-80 shrink-0 flex-col justify-between rounded-xl border-2 border-border bg-background p-6 text-foreground shadow-[var(--hard)]"
            >
              <p className="font-mono text-sm font-medium">{item.cite}</p>
              <h3 className="font-heading text-2xl leading-tight tracking-tighter">{item.name}</h3>
            </article>
          ))}
        </Marquee>
      </section>

      <section id="services" className="site-container section-pad scroll-mt-32" aria-labelledby="bento">
        <TextReveal
          id="bento"
          text="What gets checked"
          className="scroll-mt-28 font-heading text-4xl tracking-tighter text-foreground sm:text-5xl"
        />
        <div className="mt-10 grid gap-4 lg:grid-cols-12">
          <Reveal className="lg:col-span-7 lg:row-span-3">
            <article className="relative flex h-full min-h-[320px] flex-col justify-end overflow-hidden rounded-[32px] border-2 border-border bg-primary p-8 text-primary-foreground shadow-[var(--hard-lg)]">
              <div
                aria-hidden
                className="pointer-events-none absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2280%22 height=%2280%22%3E%3Cpath d=%22M0 80L80 0%22 stroke=%22%23D2E823%22 stroke-width=%222%22/%3E%3C/svg%3E')] opacity-40 mix-blend-overlay"
              />
              <p className="relative font-mono text-xs tracking-widest text-primary-foreground uppercase">
                {ruling.citation}
              </p>
              <h3 className="relative mt-3 font-heading text-4xl tracking-tighter sm:text-5xl">
                {ruling.rule}
              </h3>
              <p className="relative mt-4 max-w-md text-base leading-relaxed font-medium opacity-80">
                {ruling.body}
              </p>
            </article>
          </Reveal>
          {notes.map((check, index) => (
            <Reveal key={check.rule} delay={0.08 * (index + 1)} className="lg:col-span-5">
              <article
                className={cn(
                  'flex h-full min-h-[148px] flex-col justify-between rounded-xl border-2 border-border bg-card p-6 text-card-foreground shadow-[var(--hard)] transition-transform duration-150 hover:translate-x-1 hover:translate-y-1 hover:shadow-none',
                  check.dark && 'bg-primary text-primary-foreground',
                )}
              >
                <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                  {check.citation}
                </p>
                <div>
                  <h3 className="mt-3 font-heading text-2xl tracking-tighter">{check.rule}</h3>
                  <p className="mt-2 text-sm leading-relaxed font-medium text-muted-foreground">
                    {check.body}
                  </p>
                </div>
              </article>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="site-container pb-24" aria-labelledby="pipeline">
        <TextReveal
          id="pipeline"
          text="How the audit runs"
          className="font-heading text-4xl tracking-tighter text-foreground sm:text-5xl"
        />
        <AuditTrail />
      </section>

      <section id="story" className="scroll-mt-32 border-t-2 border-border" aria-labelledby="story-title">
        <div className="site-container grid items-center gap-10 py-20 lg:grid-cols-12 lg:gap-16 lg:py-28">
          <figure className="order-2 lg:order-1 lg:col-span-6">
            <div className="overflow-hidden rounded-[32px] border-2 border-border bg-card shadow-[var(--hard-lg)]">
              <ExhibitPhoto
                src={docketDesk}
                alt="An open black folder of blank ruled paper on a cream desk, with an acid tab, a black pencil, and a ruler."
                width={1152}
                height={864}
                className="aspect-[4/3] w-full object-cover"
              />
            </div>
            <figcaption className="mt-3 font-mono text-xs tracking-[0.16em] text-muted-foreground uppercase">
              The working file
            </figcaption>
          </figure>
          <div className="order-1 lg:order-2 lg:col-span-5 lg:col-start-8">
            <p className="font-mono text-xs tracking-[0.18em] text-emphasis uppercase">{STORY.kicker}</p>
            <TextReveal
              id="story-title"
              text={STORY.title}
              className="scroll-mt-28 mt-4 font-heading text-4xl tracking-tighter text-foreground sm:text-5xl"
            />
            <p className="mt-6 text-lg leading-relaxed font-medium text-foreground">{STORY.body}</p>
            <p className="mt-8 border-l-2 border-border pl-4 font-heading text-2xl tracking-tighter text-foreground">
              {STORY.aside}
            </p>
          </div>
        </div>
      </section>

      <section id="showcase" className="site-container scroll-mt-32 pb-20" aria-labelledby="showcase-title">
        <TextReveal
          id="showcase-title"
          text="From the sample statement"
          className="scroll-mt-28 font-heading text-4xl tracking-tighter text-foreground sm:text-5xl"
        />
        <figure className="mt-10">
          <div className="overflow-hidden rounded-[32px] border-2 border-border bg-card shadow-[var(--hard-lg)]">
            <ExhibitPhoto
              src={ledgerStack}
              alt="A stack of cream sheets on a black table. The top sheet has one acid bar and one black underline."
              width={1280}
              height={720}
              className="aspect-[16/9] w-full object-cover"
            />
          </div>
          <figcaption className="mt-3 font-mono text-xs tracking-[0.16em] text-muted-foreground uppercase">
            Marked, then priced
          </figcaption>
        </figure>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {SHOWCASE.map((item, index) => (
            <Reveal key={item.code} delay={index * 0.06}>
              <article className="flex h-full flex-col justify-between rounded-xl border-2 border-border bg-card p-6 text-card-foreground shadow-[var(--hard)] transition-transform duration-150 hover:translate-x-1 hover:translate-y-1 hover:shadow-none">
                <p className="font-heading text-5xl tracking-tighter text-emphasis">{item.code}</p>
                <div className="mt-10">
                  <h3 className="font-heading text-xl tracking-tighter">{item.title}</h3>
                  <p className="mt-2 font-mono text-sm text-muted-foreground">{item.detail}</p>
                </div>
              </article>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="proof" className="scroll-mt-32 border-t-2 border-border bg-card" aria-labelledby="proof-title">
        <div className="site-container py-20 lg:py-24">
          <div className="grid items-start gap-8 lg:grid-cols-12 lg:gap-x-10">
            <div className="lg:col-span-7">
              <p className="font-mono text-xs tracking-[0.18em] text-emphasis uppercase">Sample notes</p>
              <TextReveal
                id="proof-title"
                text="What the work sounds like"
                className="scroll-mt-28 mt-4 font-heading text-4xl tracking-tighter text-foreground sm:text-5xl"
              />
              <ul className="mt-10 grid gap-4">
                {NOTES.map((note, index) => (
                  <li key={note.quote}>
                    <Reveal delay={index * 0.06}>
                      <blockquote className="flex h-full flex-col justify-between rounded-xl border-2 border-border bg-background p-6 text-foreground shadow-[var(--hard)]">
                        <p className="text-lg leading-relaxed font-medium">“{note.quote}”</p>
                        <footer className="mt-8 font-mono text-xs tracking-widest text-muted-foreground uppercase">
                          {note.by}
                          <span className="mx-2">/</span>
                          {note.role}
                        </footer>
                      </blockquote>
                    </Reveal>
                  </li>
                ))}
              </ul>
            </div>
            <figure className="lg:col-span-5 lg:sticky lg:top-28">
              <div className="overflow-hidden rounded-xl border-2 border-border bg-background shadow-[var(--hard)]">
                <ExhibitPhoto
                  src={lineMarkup}
                  alt="A close crop of cream paper. One blank row is marked with a black line and a short acid bar."
                  width={864}
                  height={1152}
                  className="aspect-[3/4] w-full"
                />
              </div>
              <figcaption className="mt-3 font-mono text-xs tracking-[0.16em] text-muted-foreground uppercase lg:text-right">
                One line, one mark
              </figcaption>
            </figure>
          </div>
        </div>
      </section>

      <section id="security" className="scroll-mt-32 border-t-2 border-border" aria-labelledby="security-title">
        <div className="site-container py-20 lg:py-24">
          <p className="font-mono text-xs tracking-[0.18em] text-emphasis uppercase">The lock on the file</p>
          <TextReveal
            id="security-title"
            text="What the site actually enforces"
            className="scroll-mt-28 mt-4 max-w-3xl font-heading text-4xl tracking-tighter text-foreground sm:text-5xl"
          />
          <ul className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-6">
            {SECURITY.map((item, index) => (
              <li key={item.k} className={index < 2 ? 'lg:col-span-3' : 'lg:col-span-2'}>
                <Reveal delay={index * 0.05}>
                  <article className="flex h-full flex-col justify-between rounded-xl border-2 border-border bg-card p-6 text-card-foreground shadow-[var(--hard)]">
                    <p className="font-heading text-4xl tracking-tighter text-emphasis">{item.k}</p>
                    <div className="mt-8">
                      <h3 className="font-heading text-2xl tracking-tighter text-foreground">{item.title}</h3>
                      <p className="mt-2 text-sm leading-relaxed font-medium text-muted-foreground">{item.body}</p>
                    </div>
                  </article>
                </Reveal>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section id="start" className="border-y-2 border-border bg-primary text-primary-foreground" aria-labelledby="start-title">
        <div className="site-container flex flex-col gap-8 py-16 sm:flex-row sm:items-end sm:justify-between lg:py-20">
          <div className="max-w-2xl">
            <h2 id="start-title" className="font-heading text-4xl tracking-tighter sm:text-6xl">
              Put the next bill on the record.
            </h2>
            <p className="mt-4 max-w-lg text-base leading-relaxed font-medium opacity-80">
              Upload a bill and an explanation of benefits. The pipeline prepares the docket and waits for a signature.
            </p>
          </div>
          <div className="flex flex-wrap gap-4">
            <HardShadowButton to="/upload" tone="paper">
              Start an audit
            </HardShadowButton>
            <HardShadowButton to="/claims">View the ledger</HardShadowButton>
          </div>
        </div>
      </section>
    </div>
  )
}
