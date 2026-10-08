import { motion, useReducedMotion, type Variants } from 'motion/react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

const wordVariants: Variants = {
  hidden: { y: '110%' },
  show: {
    y: '0%',
    transition: { duration: 0.55, ease: [0.16, 1, 0.3, 1] },
  },
}

/**
 * Line-stable word reveal. Each word sits in an overflow-hidden box so the
 * slide does not change the heading's height. Reduced motion prints the text.
 */
export function TextReveal({
  text,
  as: Tag = 'h2',
  className,
  id,
  play = 'view',
}: {
  text: string
  as?: 'h1' | 'h2' | 'h3' | 'p'
  className?: string
  id?: string
  play?: 'view' | 'mount'
}) {
  const reduceMotion = useReducedMotion()
  const lines = text.split('\n')
  const MotionTag = motion[Tag]

  if (reduceMotion) {
    return (
      <Tag id={id} className={className}>
        {lines.map((line, index) => (
          <span key={index} className="block">
            {line}
          </span>
        ))}
      </Tag>
    )
  }

  const words = lines.map((line) => line.split(' ').filter(Boolean))
  const total = words.reduce((count, line) => count + line.length, 0)
  const stagger = Math.min(0.07, 0.42 / Math.max(total, 1))

  return (
    <MotionTag
      id={id}
      className={className}
      initial="hidden"
      animate={play === 'mount' ? 'show' : undefined}
      whileInView={play === 'view' ? 'show' : undefined}
      viewport={play === 'view' ? { once: true, margin: '-40px' } : undefined}
      variants={{
        hidden: {},
        show: { transition: { staggerChildren: stagger, delayChildren: 0.04 } },
      }}
      aria-label={text.replaceAll('\n', ' ')}
    >
      {words.map((line, lineIndex) => (
        <span key={lineIndex} className="block" aria-hidden>
          {line.map((word, wordIndex) => (
            <span key={`${word}-${wordIndex}`}>
              <span className="inline-block overflow-hidden align-bottom pb-[0.06em]">
                <motion.span variants={wordVariants} className="inline-block transform-gpu">
                  {word}
                </motion.span>
              </span>
              {wordIndex < line.length - 1 ? ' ' : null}
            </span>
          ))}
        </span>
      ))}
    </MotionTag>
  )
}

export function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode
  className?: string
  delay?: number
}) {
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      className={cn('transform-gpu', className)}
      initial={reduceMotion ? false : { opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.45, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  )
}
