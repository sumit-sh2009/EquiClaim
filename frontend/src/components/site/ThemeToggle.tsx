import { useTheme } from 'next-themes'
import { AnimatedThemeToggler } from '@/components/ui/animated-theme-toggler'
import { cn } from '@/lib/utils'

/**
 * Day/night switch for the evidence room. next-themes owns persistence and
 * the `dark` class; the toggler owns the reveal — the incoming theme is
 * clipped in from the button itself via the View Transitions API, so the
 * change reads as a wipe of light across the room rather than a flash.
 * Browsers without View Transitions (and reduced-motion users) just swap.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, setTheme } = useTheme()
  const theme = resolvedTheme === 'light' ? 'light' : 'dark'

  return (
    <AnimatedThemeToggler
      theme={theme}
      onThemeChange={setTheme}
      duration={520}
      variant="circle"
      aria-label={theme === 'dark' ? 'Switch to daylight' : 'Switch to night'}
      title={theme === 'dark' ? 'Daylight' : 'Night'}
      className={cn(
        'inline-flex size-10 shrink-0 items-center justify-center rounded-xl border-2 border-border bg-card text-card-foreground shadow-[2px_2px_0_0_var(--border)]',
        'transition-colors hover:bg-accent hover:text-accent-foreground',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
        '[&_svg]:size-4',
        className,
      )}
    />
  )
}
