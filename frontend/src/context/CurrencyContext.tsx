import React, { createContext, useContext, useEffect, useState } from 'react'
import {
  CurrencyCode,
  CurrencyConfig,
  DEFAULT_CURRENCY,
  SUPPORTED_CURRENCIES,
  convertCentsFromUsd,
  formatCents,
} from '@/lib/currency'

interface CurrencyContextValue {
  currency: CurrencyCode
  setCurrency: (currency: CurrencyCode) => void
  currencies: CurrencyConfig[]
  config: CurrencyConfig
  format: (usdCents: number, targetCurrency?: CurrencyCode) => string
  convert: (usdCents: number, targetCurrency?: CurrencyCode) => number
  symbol: string
}

const STORAGE_KEY = 'equiclaim_currency'

const CurrencyContext = createContext<CurrencyContextValue | null>(null)

export function CurrencyProvider({ children }: { children: React.ReactNode }) {
  const [currency, setCurrencyState] = useState<CurrencyCode>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved && saved in SUPPORTED_CURRENCIES) {
        return saved as CurrencyCode
      }
    } catch {
      // LocalStorage not available or blocked
    }
    return DEFAULT_CURRENCY
  })

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, currency)
    } catch {
      // Ignore storage errors
    }
  }, [currency])

  const setCurrency = (newCurrency: CurrencyCode) => {
    if (newCurrency in SUPPORTED_CURRENCIES) {
      setCurrencyState(newCurrency)
    }
  }

  const config = SUPPORTED_CURRENCIES[currency] ?? SUPPORTED_CURRENCIES.USD

  const format = (usdCents: number, targetCurrency?: CurrencyCode): string => {
    const target = targetCurrency ?? currency
    const converted = convertCentsFromUsd(usdCents, target)
    return formatCents(converted, target)
  }

  const convert = (usdCents: number, targetCurrency?: CurrencyCode): number => {
    return convertCentsFromUsd(usdCents, targetCurrency ?? currency)
  }

  const value: CurrencyContextValue = {
    currency,
    setCurrency,
    currencies: Object.values(SUPPORTED_CURRENCIES),
    config,
    format,
    convert,
    symbol: config.symbol,
  }

  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>
}

export function useCurrency(): CurrencyContextValue {
  const context = useContext(CurrencyContext)
  if (!context) {
    // Provide a safe fallback if rendered outside provider
    const config = SUPPORTED_CURRENCIES.USD
    return {
      currency: 'USD',
      setCurrency: () => {},
      currencies: Object.values(SUPPORTED_CURRENCIES),
      config,
      format: (usdCents: number) => formatCents(usdCents, 'USD'),
      convert: (usdCents: number) => usdCents,
      symbol: '$',
    }
  }
  return context
}
