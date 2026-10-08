import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { HardShadowButton } from '@/components/ui/hard-shadow-button'

const FOOTER_NAV = [
  { href: '/upload', label: 'New audit' },
  { href: '/claims', label: 'Ledger' },
  { href: '/#services', label: 'Method' },
  { href: '/#story', label: 'Approach' },
  { href: '/#security', label: 'Security' },
] as const

const FOOTER_CONTACT = [
  { label: 'Email', value: 'hello@equiclaim.local', href: 'mailto:hello@equiclaim.local' },
  { label: 'Subject', value: 'Docket alerts' },
] as const

export function SiteFooter() {
  const [email, setEmail] = useState('')

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    const subject = encodeURIComponent('Docket alerts')
    const body = encodeURIComponent(`Please send docket alerts to ${email}`)
    window.location.href = `mailto:hello@equiclaim.local?subject=${subject}&body=${body}`
  }

  return (
    <footer className="bg-ink text-ink-foreground">
      <div className="site-container section-pad">
        <div className="grid gap-12 md:grid-cols-12">
          <div className="min-w-0 md:col-span-4">
            <p className="font-heading text-3xl tracking-tighter">EquiClaim</p>
            <p className="mt-4 max-w-xs font-sans text-sm font-normal normal-case tracking-normal text-ink-muted">
              Forensic audit engine for hospital bills. CMS price files, 45 CFR § 149, NCCI edits —
              then a human signs the docket.
            </p>
          </div>
          <div className="min-w-0 md:col-span-2">
            <p className="font-mono text-xs tracking-widest text-audit-on-ink uppercase">Visit</p>
            <nav aria-label="Footer" className="mt-4 flex flex-col gap-3 font-heading text-sm tracking-wider uppercase">
              {FOOTER_NAV.map((item) => (
                <Link key={item.href} to={item.href} className="hover:text-audit-on-ink">
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="min-w-0 md:col-span-3">
            <p className="font-mono text-xs tracking-widest text-audit-on-ink uppercase">Contact</p>
            <ul className="mt-4 flex flex-col gap-3 text-sm">
              {FOOTER_CONTACT.map((item) => (
                <li key={item.label}>
                  <span className="font-mono text-xs tracking-widest text-ink-muted uppercase">{item.label}</span>
                  {'href' in item ? (
                    <a href={item.href} className="mt-1 block break-words font-heading tracking-wider uppercase hover:text-audit-on-ink">
                      {item.value}
                    </a>
                  ) : (
                    <p className="mt-1 font-heading tracking-wider uppercase">{item.value}</p>
                  )}
                </li>
              ))}
            </ul>
          </div>
          <div className="min-w-0 md:col-span-3">
            <p className="font-mono text-xs tracking-widest text-audit-on-ink uppercase">Social</p>
            <nav aria-label="Social" className="mt-4 flex flex-col gap-3 font-heading text-sm tracking-wider uppercase">
              <a href="mailto:hello@equiclaim.local" className="hover:text-audit-on-ink">
                Email
              </a>
              <span className="text-ink-muted">CMS · NSA · NCCI</span>
            </nav>
          </div>
        </div>

        <form onSubmit={onSubmit} className="mt-16 flex flex-col gap-3 sm:flex-row sm:items-stretch">
          <label className="sr-only" htmlFor="docket-email">
            Email for docket alerts
          </label>
          <input
            id="docket-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@firm.com"
            className="min-h-14 flex-1 border-2 border-ink-foreground bg-transparent px-4 font-sans text-ink-foreground placeholder:text-ink-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-audit-on-ink"
          />
          <HardShadowButton
            type="submit"
            className="bg-accent text-accent-foreground shadow-[4px_4px_0_0_var(--accent)] hover:shadow-none"
          >
            Subscribe
          </HardShadowButton>
        </form>

        <p className="mt-12 font-mono text-xs tracking-widest text-ink-muted uppercase">
          Dockets are decision-support — not legal advice.
        </p>
      </div>
    </footer>
  )
}
