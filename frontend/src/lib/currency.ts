/**
 * Multi-currency configuration, exchange rates, and formatting utilities for EquiClaim.
 *
 * All claim figures are stored internally as integer cents (minor units) in USD.
 * This module enables real-time conversions and locale-aware formatting across
 * global healthcare markets and jurisdictions.
 */

export interface CurrencyConfig {
  code: string
  symbol: string
  name: string
  decimals: number
  rateToUsd: number // Foreign currency units per 1.00 USD
  locale: string
  flag: string
}

export const SUPPORTED_CURRENCIES: Record<string, CurrencyConfig> = {
  USD: {
    code: 'USD',
    symbol: '$',
    name: 'US Dollar',
    decimals: 2,
    rateToUsd: 1.0,
    locale: 'en-US',
    flag: '🇺🇸',
  },
  EUR: {
    code: 'EUR',
    symbol: '€',
    name: 'Euro',
    decimals: 2,
    rateToUsd: 0.92,
    locale: 'de-DE',
    flag: '🇪🇺',
  },
  GBP: {
    code: 'GBP',
    symbol: '£',
    name: 'British Pound',
    decimals: 2,
    rateToUsd: 0.79,
    locale: 'en-GB',
    flag: '🇬🇧',
  },
  CAD: {
    code: 'CAD',
    symbol: 'CA$',
    name: 'Canadian Dollar',
    decimals: 2,
    rateToUsd: 1.36,
    locale: 'en-CA',
    flag: '🇨🇦',
  },
  AUD: {
    code: 'AUD',
    symbol: 'AU$',
    name: 'Australian Dollar',
    decimals: 2,
    rateToUsd: 1.52,
    locale: 'en-AU',
    flag: '🇦🇺',
  },
  INR: {
    code: 'INR',
    symbol: '₹',
    name: 'Indian Rupee',
    decimals: 2,
    rateToUsd: 83.5,
    locale: 'en-IN',
    flag: '🇮🇳',
  },
  JPY: {
    code: 'JPY',
    symbol: '¥',
    name: 'Japanese Yen',
    decimals: 0,
    rateToUsd: 155.0,
    locale: 'ja-JP',
    flag: '🇯🇵',
  },
  CHF: {
    code: 'CHF',
    symbol: 'CHF',
    name: 'Swiss Franc',
    decimals: 2,
    rateToUsd: 0.9,
    locale: 'de-CH',
    flag: '🇨🇭',
  },
}

export type CurrencyCode = keyof typeof SUPPORTED_CURRENCIES

export const DEFAULT_CURRENCY: CurrencyCode = 'USD'

/**
 * Convert USD cents (integer) into the minor units of a target currency.
 */
export function convertCentsFromUsd(
  usdCents: number,
  targetCurrency: CurrencyCode = 'USD',
): number {
  if (targetCurrency === 'USD') return usdCents
  const target = SUPPORTED_CURRENCIES[targetCurrency] ?? SUPPORTED_CURRENCIES.USD

  // USD dollars = usdCents / 100
  const usdDollars = usdCents / 100
  const foreignMajor = usdDollars * target.rateToUsd
  const scale = 10 ** target.decimals
  return Math.round(foreignMajor * scale)
}

/**
 * Convert minor units of a given currency back into USD cents.
 */
export function convertCentsToUsd(
  minorUnits: number,
  fromCurrency: CurrencyCode = 'USD',
): number {
  if (fromCurrency === 'USD') return minorUnits
  const from = SUPPORTED_CURRENCIES[fromCurrency] ?? SUPPORTED_CURRENCIES.USD
  const scale = 10 ** from.decimals
  const fromMajor = minorUnits / scale
  const usdMajor = fromMajor / from.rateToUsd
  return Math.round(usdMajor * 100)
}

/**
 * Format an integer minor-unit amount in the specified currency.
 */
export function formatCents(
  cents: number,
  currencyCode: CurrencyCode = 'USD',
): string {
  const config = SUPPORTED_CURRENCIES[currencyCode] ?? SUPPORTED_CURRENCIES.USD
  const scale = 10 ** config.decimals
  const major = cents / scale

  try {
    return new Intl.NumberFormat(config.locale, {
      style: 'currency',
      currency: config.code,
      minimumFractionDigits: config.decimals,
      maximumFractionDigits: config.decimals,
    }).format(major)
  } catch {
    // Fallback if environment lacks locale data
    return `${config.symbol}${major.toLocaleString('en-US', {
      minimumFractionDigits: config.decimals,
      maximumFractionDigits: config.decimals,
    })}`
  }
}
