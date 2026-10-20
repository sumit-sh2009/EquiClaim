import { cn } from '@/lib/utils'
import { NumberTicker } from '@/components/ui/number-ticker'
import { CurrencyCode, formatCents as libFormatCents } from '@/lib/currency'
import { useCurrency } from '@/context/CurrencyContext'

export function formatCents(cents: number, currency: CurrencyCode = 'USD'): string {
  return libFormatCents(cents, currency)
}

/**
 * Money always sets in tabular figures so columns of amounts align.
 * Reacts automatically to the globally active currency selected by the user.
 */
export function Money({
  cents,
  className,
  currency: explicitCurrency,
}: {
  cents: number
  className?: string
  currency?: CurrencyCode
}) {
  const { format, currency: activeCurrency } = useCurrency()

  if (explicitCurrency) {
    return (
      <span className={cn('tnum', className)}>
        {format(cents, explicitCurrency)}
      </span>
    )
  }

  return (
    <span className={cn('tnum', className)} data-currency={activeCurrency}>
      {format(cents)}
    </span>
  )
}

/**
 * Money that counts up when scrolled into view. Reserved for hero figures —
 * tables stay quiet. Screen readers get the settled value up front.
 * Adapts to active currency symbols, rates, and decimals.
 */
export function AnimatedMoney({
  cents,
  className,
  delay = 0,
  currency: explicitCurrency,
}: {
  cents: number
  className?: string
  delay?: number
  currency?: CurrencyCode
}) {
  const { convert, config, currency: activeCurrency } = useCurrency()
  const targetCurrency = explicitCurrency ?? activeCurrency
  const convertedMinor = convert(cents, targetCurrency)
  const scale = 10 ** config.decimals
  const displayValue = convertedMinor / scale

  return (
    <span className={cn('tnum', className)} aria-label={libFormatCents(convertedMinor, targetCurrency)}>
      <span aria-hidden>
        {config.symbol}
        <NumberTicker
          value={displayValue}
          decimalPlaces={config.decimals}
          delay={delay}
        />
      </span>
    </span>
  )
}
