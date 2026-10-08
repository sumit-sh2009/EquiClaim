import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link, type LinkProps } from 'react-router-dom'
import { cn } from '@/lib/utils'

type Base = {
  children: ReactNode
  className?: string
  tone?: 'ink' | 'paper'
}

type AsLink = Base & { to: LinkProps['to'] } & Omit<LinkProps, 'to' | 'children' | 'className'>
type AsButton = Base & ButtonHTMLAttributes<HTMLButtonElement> & { to?: undefined }

export type HardShadowButtonProps = AsLink | AsButton

/** Tactile neo-brutalist CTA — ink fill, acid type, hard shadow that presses in. */
export function HardShadowButton(props: HardShadowButtonProps) {
  const { children, className, tone = 'ink' } = props
  const cls = cn('hard-shadow-btn', tone === 'paper' && 'hard-shadow-btn--paper', className)

  if ('to' in props && props.to !== undefined) {
    const { to, className: _c, children: _ch, tone: _t, ...linkProps } = props
    return (
      <Link to={to} className={cls} {...linkProps}>
        {children}
      </Link>
    )
  }

  const { type = 'button', className: _cb, children: _chb, tone: _tb, ...buttonProps } = props as AsButton
  return (
    <button type={type} className={cls} {...buttonProps}>
      {children}
    </button>
  )
}
