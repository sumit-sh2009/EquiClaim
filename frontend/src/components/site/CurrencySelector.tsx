import { useEffect, useRef, useState } from 'react'
import { Coins, Check, ChevronDown } from 'lucide-react'
import { useCurrency } from '@/context/CurrencyContext'
import { CurrencyCode } from '@/lib/currency'
import { cn } from '@/lib/utils'

export function CurrencySelector({ className }: { className?: string }) {
  const { currency, setCurrency, currencies } = useCurrency()
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open])

  // Close on escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setOpen(false)
      }
    }
    if (open) {
      document.addEventListener('keydown', handleKeyDown)
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  return (
    <div ref={containerRef} className={cn('relative inline-block', className)}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label="Select currency"
        className={cn(
          'inline-flex min-h-11 items-center justify-between gap-1.5 rounded-xl border-2 border-border bg-card px-2.5 py-2 font-heading text-xs tracking-tighter text-card-foreground shadow-[2px_2px_0_0_var(--border)] transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring',
        )}
      >
        <span className="flex items-center gap-1.5 font-mono text-xs font-medium">
          <Coins className="size-3.5 text-muted-foreground" aria-hidden />
          <span>{currency}</span>
          <span className="font-sans text-[11px] text-muted-foreground">({currencies.find((c) => c.code === currency)?.symbol})</span>
        </span>
        <ChevronDown
          className={cn('size-3 text-muted-foreground transition-transform duration-200', open && 'rotate-180')}
          aria-hidden
        />
      </button>

      {open && (
        <div
          role="listbox"
          aria-label="Available currencies"
          className="absolute right-0 top-full z-50 mt-2 w-48 rounded-xl border-2 border-border bg-card p-1.5 text-card-foreground shadow-[4px_4px_0_0_var(--border)] backdrop-blur-md animate-in fade-in zoom-in-95 duration-100"
        >
          <div className="px-2 py-1 text-[10px] font-heading uppercase tracking-wider text-muted-foreground">
            Display Currency
          </div>
          <div className="flex flex-col gap-0.5">
            {currencies.map((item) => {
              const selected = item.code === currency
              return (
                <button
                  key={item.code}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => {
                    setCurrency(item.code as CurrencyCode)
                    setOpen(false)
                  }}
                  className={cn(
                    'flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-xs font-heading transition-colors',
                    selected
                      ? 'bg-accent text-accent-foreground font-semibold'
                      : 'hover:bg-muted text-card-foreground',
                  )}
                >
                  <span className="flex items-center gap-2">
                    <span className="text-sm">{item.flag}</span>
                    <span className="font-mono">{item.code}</span>
                    <span className="text-[11px] text-muted-foreground">({item.symbol})</span>
                  </span>
                  {selected && <Check className="size-3 text-accent-foreground" aria-hidden />}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
