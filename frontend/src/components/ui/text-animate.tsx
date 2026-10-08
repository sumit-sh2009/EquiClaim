import { memo } from 'react'
import { motion, useReducedMotion, type Variants } from 'motion/react'

import { cn } from '@/lib/utils'
import { textSegmentVariants, type TextAnimationVariant } from '@/components/ui/text-motion'

type AnimationType = 'text' | 'word' | 'character'

interface TextAnimateProps {
  /** The text content to animate. */
  children: string
  className?: string
  /** Class applied to each segment. */
  segmentClassName?: string
  /** Delay before the animation starts (seconds). */
  delay?: number
  /** Total stagger window (seconds). */
  duration?: number
  /** Element type to render. */
  as?: 'h1' | 'h2' | 'h3' | 'p' | 'span' | 'div'
  /** id for the rendered element (e.g. an aria-labelledby target). */
  id?: string
  /** How to split the text. */
  by?: AnimationType
  /** Animate only once. */
  once?: boolean
  /** Animation preset. blurInUp/slideUp use spring physics; fadeIn eases. */
  animation?: TextAnimationVariant
}

/**
 * Word/character staggered text entrance. Screen readers get the full string
 * via sr-only; animated segments are aria-hidden. Static under reduced motion.
 */
export const TextAnimate = memo(function TextAnimate({
  children,
  delay = 0,
  duration = 0.4,
  className,
  segmentClassName,
  as: Component = 'p',
  id,
  by = 'word',
  once = true,
  animation = 'blurInUp',
}: TextAnimateProps) {
  const reduceMotion = useReducedMotion()
  const MotionComponent = motion[Component]

  if (reduceMotion) {
    return (
      <Component id={id} className={className}>
        {children}
      </Component>
    )
  }

  const segments =
    by === 'word' ? children.split(/(\s+)/) : by === 'character' ? children.split('') : [children]

  const container: Variants = {
    hidden: { opacity: 1 },
    show: {
      opacity: 1,
      transition: { delayChildren: delay, staggerChildren: duration / segments.length },
    },
  }

  return (
    <MotionComponent
      id={id}
      variants={container}
      initial="hidden"
      whileInView="show"
      viewport={{ once, margin: '-40px' }}
      className={cn('whitespace-pre-wrap', className)}
      aria-label={children}
    >
      <span className="sr-only">{children}</span>
      {segments.map((segment, i) => (
        <motion.span
          key={`${by}-${i}`}
          variants={textSegmentVariants[animation]}
          className={cn('inline-block whitespace-pre', segmentClassName)}
          aria-hidden
        >
          {segment}
        </motion.span>
      ))}
    </MotionComponent>
  )
})
