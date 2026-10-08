import type { CSSProperties, InputHTMLAttributes } from 'react'
import { BrutalistInput } from '@/components/ui/brutalist-input'
import { cn } from '@/lib/utils'
import './ccn-card.css'

export interface CcnCardProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  error?: string
  invalid?: boolean
  submitLabel?: string
}

/**
 * Brutalist CCN intake card — Uiverse.io by 0xnihilism, on lit paper tokens.
 */
export function CcnCard({
  id,
  error,
  invalid,
  submitLabel = 'Continue',
  className,
  ...inputProps
}: CcnCardProps) {
  return (
    <div
      className={cn('ccn-card', invalid && 'ccn-card--invalid', className)}
      style={
        {
          '--ccn-bg': 'var(--paper)',
          '--ccn-ink': 'var(--paper-ink)',
          '--ccn-accent': 'oklch(0.72 0.17 145)',
          '--ccn-accent-bright': 'oklch(0.86 0.22 142)',
        } as CSSProperties
      }
    >
      <span className="ccn-card__title">Hospital CCN</span>
      <p className="ccn-card__content">
        The 6–10 digit CMS certification number on the bill header. We use it to pull the
        hospital&rsquo;s published price file.
      </p>
      <div className="ccn-card__form">
        <BrutalistInput
          {...inputProps}
          id={id}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          spellCheck={false}
          placeholder="450123"
          invalid={invalid}
          aria-invalid={invalid || undefined}
          aria-describedby={error ? `${id}-error` : undefined}
        />
        {error ? (
          <p id={`${id}-error`} role="alert" className="ccn-card__error">
            {error}
          </p>
        ) : null}
        <button type="submit" className="ccn-card__button" disabled={inputProps.disabled}>
          {submitLabel}
        </button>
      </div>
    </div>
  )
}
