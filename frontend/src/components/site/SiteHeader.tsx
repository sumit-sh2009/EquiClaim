import { motion } from 'motion/react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { HardShadowButton } from '@/components/ui/hard-shadow-button'
import { ThemeToggle } from '@/components/site/ThemeToggle'
import { CurrencySelector } from '@/components/site/CurrencySelector'
import { cn } from '@/lib/utils'

const LANDING_LINKS = [
  { href: '/#services', label: 'Method' },
  { href: '/#story', label: 'Approach' },
  { href: '/#proof', label: 'Notes' },
  { href: '/#security', label: 'Security' },
] as const

const actionLink =
  'inline-flex min-h-11 items-center justify-center rounded-xl border-2 border-border bg-card px-3 py-2 text-center font-heading text-xs tracking-tighter text-card-foreground shadow-[2px_2px_0_0_var(--border)] transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring'

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
    <header className="sticky top-0 z-40 bg-background pt-3 sm:pt-4">
      <div className="mx-3 flex flex-col gap-3 rounded-xl border-2 border-border bg-background/95 px-3 py-3 text-foreground shadow-[2px_2px_0_0_var(--border)] backdrop-blur-[24px] sm:mx-4 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:px-4">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-2 focus:z-50 focus:rounded-xl focus:bg-accent focus:px-3 focus:py-2 focus:text-accent-foreground"
        >
          Skip to content
        </a>
        <div className="flex min-w-0 items-center justify-between gap-3">
          <Link
            to="/"
            className="min-w-0 truncate font-heading text-lg tracking-tighter text-foreground sm:text-2xl"
            aria-label="EquiClaim home"
          >
            EQUICLAIM
          </Link>
          <div className="flex items-center gap-2 sm:hidden">
            <CurrencySelector />
            <ThemeToggle className="size-11" />
          </div>
        </div>

        <nav aria-label="Primary" className="flex min-w-0 items-center gap-2 sm:gap-3">
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
              className={({ isActive }) => cn('relative', actionLink, isActive && 'bg-accent text-accent-foreground')}
            >
              LEDGER
              {ledgerActive ? <NavUnderline /> : null}
            </NavLink>
          </div>

          <div className="grid w-full grid-cols-2 gap-2 sm:hidden">
            <NavLink
              to="/claims"
              className={({ isActive }) => cn(actionLink, isActive && 'bg-accent text-accent-foreground')}
            >
              Ledger
            </NavLink>
            <HardShadowButton to="/upload" className="min-h-11 w-full !px-3 !py-2 text-xs">
              New audit
            </HardShadowButton>
          </div>

          <NavLink
            to="/claims"
            className={({ isActive }) =>
              cn(actionLink, 'hidden sm:inline-flex lg:hidden', isActive && 'bg-accent text-accent-foreground')
            }
          >
            Ledger
          </NavLink>
          <CurrencySelector className="hidden sm:inline-flex" />
          <ThemeToggle className="hidden sm:inline-flex" />
          <HardShadowButton to="/upload" className="hidden min-h-11 !px-4 !py-2 text-xs sm:inline-flex">
            New audit
          </HardShadowButton>
        </nav>
      </div>
      {onHome ? (
        <nav
          aria-label="On this page"
          className="mx-3 mt-2 flex snap-x gap-1 overflow-x-auto px-1 pb-1 [-ms-overflow-style:none] [scrollbar-width:none] lg:hidden [&::-webkit-scrollbar]:hidden"
        >
          {LANDING_LINKS.map((item) => (
            <Link
              key={item.href}
              to={item.href}
              className="inline-flex min-h-11 shrink-0 snap-start items-center px-2 font-heading text-xs tracking-tighter text-foreground underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </header>
  )
}
