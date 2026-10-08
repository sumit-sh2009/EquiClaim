import { useRef, type ComponentPropsWithoutRef } from 'react'
import { useInView } from 'motion/react'

import { cn } from '@/lib/utils'

interface MarqueeProps extends ComponentPropsWithoutRef<'div'> {
  className?: string
  /** Reverse the animation direction. */
  reverse?: boolean
  /** Pause the animation on hover. */
  pauseOnHover?: boolean
  children: React.ReactNode
  /** Animate vertically instead of horizontally. */
  vertical?: boolean
  /** Number of times to repeat the content. */
  repeat?: number
}

/**
 * Infinite scroll strip. Runs only while in the viewport (animation-play-state
 * is paused offscreen so the loop never burns frames nobody sees), pauses on
 * hover when asked, and CSS freezes it fully under prefers-reduced-motion.
 */
export function Marquee({
  className,
  reverse = false,
  pauseOnHover = false,
  children,
  vertical = false,
  repeat = 4,
  ...props
}: MarqueeProps) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref)

  return (
    <div
      {...props}
      ref={ref}
      className={cn(
        'group flex gap-(--gap) overflow-hidden p-2 [--duration:40s] [--gap:1rem]',
        vertical ? 'flex-col' : 'flex-row',
        className,
      )}
    >
      {Array(repeat)
        .fill(0)
        .map((_, i) => (
          <div
            key={i}
            aria-hidden={i > 0}
            className={cn('flex shrink-0 justify-around gap-(--gap) will-change-transform', {
              'animate-marquee flex-row': !vertical,
              'animate-marquee-vertical flex-col': vertical,
              'group-hover:[animation-play-state:paused]': pauseOnHover,
              '[animation-direction:reverse]': reverse,
              '[animation-play-state:paused]': !inView,
            })}
          >
            {children}
          </div>
        ))}
    </div>
  )
}
