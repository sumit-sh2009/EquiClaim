import type { Variants } from 'motion/react'

/**
 * Shared physics for staggered text entrances: a firm spring that settles
 * without overshoot theatrics. blurInUp/slideUp ride the spring; fadeIn
 * keeps the standard 300ms ease for places where physics would shout.
 */
export const textSpringTransition = {
  type: 'spring',
  stiffness: 120,
  damping: 20,
  mass: 0.9,
} as const

export type TextAnimationVariant = 'fadeIn' | 'blurInUp' | 'slideUp'

export const textSegmentVariants: Record<TextAnimationVariant, Variants> = {
  fadeIn: {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.2, 0.6, 0.2, 1] } },
  },
  blurInUp: {
    hidden: { opacity: 0, filter: 'blur(8px)', y: 14 },
    show: { opacity: 1, filter: 'blur(0px)', y: 0, transition: textSpringTransition },
  },
  slideUp: {
    hidden: { y: 16, opacity: 0 },
    show: { y: 0, opacity: 1, transition: textSpringTransition },
  },
}
