import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { HardShadowButton } from '@/components/ui/hard-shadow-button'

const SUPPORT_EMAIL = 'sumit.shawsh2009@gmail.com'
const GITHUB_PROFILE = 'https://github.com/sumit-sh2009'
const GITHUB_REPO = 'https://github.com/sumit-sh2009/EquiClaim'

const FOOTER_NAV = [
  { href: '/upload', label: 'New audit' },
  { href: '/claims', label: 'Ledger' },
  { href: '/#services', label: 'Method' },
  { href: '/#story', label: 'Approach' },
  { href: '/#security', label: 'Security' },
] as const

export function SiteFooter() {
  const [email, setEmail] = useState('')

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    const subject = encodeURIComponent('EquiClaim — support')
    const body = encodeURIComponent(
      `Hi Sumit,\n\nPlease get back to me at ${email}.\n\n`,
    )
    window.location.href = `mailto:${SUPPORT_EMAIL}?subject=${subject}&body=${body}`
  }

  return (
    <footer className="bg-ink text-ink-foreground">
      <div className="site-container section-pad">
        <div className="grid gap-12 md:grid-cols-12">
          <div className="min-w-0 md:col-span-4">
            <p className="font-heading text-3xl tracking-tighter">EquiClaim</p>
            <p className="mt-4 max-w-xs font-sans text-sm font-normal normal-case tracking-normal text-ink-muted">
              Forensic audit engine for hospital bills. Built by{' '}
              <a
                href={GITHUB_PROFILE}
                className="text-ink-foreground underline decoration-audit-on-ink underline-offset-4 hover:text-audit-on-ink"
              >
                Sumit Shaw
              </a>
              . CMS price files, 45 CFR § 149, NCCI edits — then a human signs the docket.
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
            <p className="font-mono text-xs tracking-widest text-audit-on-ink uppercase">Support</p>
            <ul className="mt-4 flex flex-col gap-3 text-sm">
              <li>
                <span className="font-mono text-xs tracking-widest text-ink-muted uppercase">Email</span>
                <a
                  href={`mailto:${SUPPORT_EMAIL}`}
                  className="mt-1 block break-all font-heading text-sm tracking-wider uppercase hover:text-audit-on-ink"
                >
                  {SUPPORT_EMAIL}
                </a>
              </li>
              <li>
                <span className="font-mono text-xs tracking-widest text-ink-muted uppercase">Maker</span>
                <p className="mt-1 font-heading tracking-wider uppercase">Sumit Shaw</p>
              </li>
            </ul>
          </div>
          <div className="min-w-0 md:col-span-3">
            <p className="font-mono text-xs tracking-widest text-audit-on-ink uppercase">Social</p>
            <nav aria-label="Social" className="mt-4 flex flex-col gap-3 font-heading text-sm tracking-wider uppercase">
              <a href={GITHUB_PROFILE} className="hover:text-audit-on-ink">
                GitHub
              </a>
              <a href={GITHUB_REPO} className="hover:text-audit-on-ink">
                Source
              </a>
              <a href={`mailto:${SUPPORT_EMAIL}`} className="hover:text-audit-on-ink">
                Email
              </a>
            </nav>
          </div>
        </div>

        <form onSubmit={onSubmit} className="mt-16 flex flex-col gap-3 sm:flex-row sm:items-stretch">
          <label className="sr-only" htmlFor="docket-email">
            Your email — opens a message to support
          </label>
          <input
            id="docket-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your email — I’ll write back"
            className="min-h-14 flex-1 border-2 border-ink-foreground bg-transparent px-4 font-sans text-ink-foreground placeholder:text-ink-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-audit-on-ink"
          />
          <HardShadowButton
            type="submit"
            className="w-full bg-accent text-accent-foreground shadow-[4px_4px_0_0_var(--accent)] hover:shadow-none sm:w-auto"
          >
            Write to me
          </HardShadowButton>
        </form>

        <div className="mt-12 flex flex-col gap-2 font-mono text-xs tracking-widest text-ink-muted uppercase sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} Sumit Shaw. Built in public.</p>
          <p>Dockets are decision-support — not legal advice.</p>
        </div>
      </div>
    </footer>
  )
}
