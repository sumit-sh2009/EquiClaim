import { motion } from 'motion/react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { HardShadowButton } from '@/components/ui/hard-shadow-button'
import { ThemeToggle } from '@/components/site/ThemeToggle'
import { cn } from '@/lib/utils'

const LANDING_LINKS = [
  { href: '/#services', label: 'Method' },
  { href: '/#story', label: 'Approach' },
  { href: '/#proof', label: 'Notes' },
  { href: '/#security', label: 'Security' },
] as const

function NavUnderline() {
  return (
    <motion.span
      layoutId="nav-underline"
      className="absolute inset-x-0 -bottom-1 h-0.5 bg-accent"
      transition={{ type: 'spring', bounce: 0, visualDuration: 0.28 }}
    />
  )
}

export function SiteHeader() {
  const { pathname, hash } = useLocation()
  const onHome = pathname === '/'
  const ledgerActive = pathname === '/claims' || pathname.startsWith('/claims/')
  return (
    <header className="sticky top-0 z-40 bg-background pt-4">
      <div className="mx-4 flex items-center justify-between gap-4 rounded-xl border-2 border-border bg-background/95 px-4 py-3 shadow-[2px_2px_0_0_var(--border)] backdrop-blur-[24px] text-foreground">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-2 focus:z-50 focus:rounded-xl focus:bg-accent focus:px-3 focus:py-2 focus:text-accent-foreground"
        >
          Skip to content
        </a>
        <Link
          to="/"
          className="font-heading text-xl tracking-tighter text-foreground sm:text-2xl"
          aria-label="EquiClaim home"
        >
          EQUICLAIM
        </Link>

        <nav aria-label="Primary" className="flex items-center gap-2 sm:gap-3">
          <div className="hidden items-center gap-5 lg:flex">
            {LANDING_LINKS.map((item) => {
              const active = onHome && hash === `#${item.href.split('#')[1]}`
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className="relative font-heading text-xs tracking-tighter text-foreground underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
                >
                  {item.label}
                  {active ? <NavUnderline /> : null}
                </Link>
              )
            })}
            <NavLink
              to="/claims"
              className={({ isActive }) =>
                cn(
                  'relative rounded-xl border-2 border-border bg-card px-3 py-2 font-heading text-xs tracking-tighter text-card-foreground shadow-[2px_2px_0_0_var(--border)] transition-colors hover:bg-accent hover:text-accent-foreground',
                  isActive && 'bg-accent text-accent-foreground',
                )
              }
            >
              LEDGER
              {ledgerActive ? <NavUnderline /> : null}
            </NavLink>
          </div>
          <NavLink
            to="/claims"
            className={({ isActive }) =>
              cn(
                'rounded-xl border-2 border-border bg-card px-3 py-2 font-heading text-xs tracking-tighter text-card-foreground shadow-[2px_2px_0_0_var(--border)] transition-colors hover:bg-accent hover:text-accent-foreground lg:hidden',
                isActive && 'bg-accent text-accent-foreground',
              )
            }
          >
            LEDGER
          </NavLink>
          <ThemeToggle />
          <HardShadowButton to="/upload" className="hidden !px-4 !py-2 text-xs sm:inline-flex">
            New audit
          </HardShadowButton>
        </nav>
      </div>
      {onHome ? (
        <nav aria-label="On this page" className="mx-4 mt-2 flex gap-4 overflow-x-auto px-1 pb-1 lg:hidden">
          {LANDING_LINKS.map((item) => (
            <Link
              key={item.href}
              to={item.href}
              className="shrink-0 font-heading text-xs tracking-tighter text-foreground underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </header>
  )
}
