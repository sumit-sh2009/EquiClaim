import { useEffect, useRef } from 'react'
import { useReducedMotion } from 'motion/react'

/**
 * 32px mix-blend-difference circle. Lerps toward the pointer at 0.2 and
 * scales 2.5× over links and buttons. Disabled for touch and reduced motion.
 */
export function AcidCursor() {
  const reduceMotion = useReducedMotion()
  const elRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (reduceMotion) return
    if (window.matchMedia('(pointer: coarse)').matches) return

    const el = elRef.current
    if (!el) return

    document.documentElement.classList.add('has-acid-cursor')

    const pos = { x: window.innerWidth / 2, y: window.innerHeight / 2 }
    const target = { ...pos }
    let hovering = false
    let frame = 0

    const onMove = (e: PointerEvent) => {
      target.x = e.clientX
      target.y = e.clientY
      const node = e.target
      hovering =
        node instanceof Element && Boolean(node.closest('a, button, [role="button"], input, textarea, select'))
    }

    const tick = () => {
      pos.x += (target.x - pos.x) * 0.2
      pos.y += (target.y - pos.y) * 0.2
      const scale = hovering ? 2.5 : 1
      el.style.transform = `translate3d(${pos.x - 16}px, ${pos.y - 16}px, 0) scale(${scale})`
      frame = requestAnimationFrame(tick)
    }

    window.addEventListener('pointermove', onMove, { passive: true })
    frame = requestAnimationFrame(tick)

    return () => {
      document.documentElement.classList.remove('has-acid-cursor')
      window.removeEventListener('pointermove', onMove)
      cancelAnimationFrame(frame)
    }
  }, [reduceMotion])

  if (reduceMotion) return null

  return (
    <div
      ref={elRef}
      aria-hidden
      className="pointer-events-none fixed top-0 left-0 z-[200] hidden size-8 rounded-full bg-white mix-blend-difference md:block"
    />
  )
}
