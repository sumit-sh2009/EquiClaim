import { useId, type ComponentProps } from 'react'

import { cn } from '@/lib/utils'

interface NoiseTextureProps extends ComponentProps<'svg'> {
  frequency?: number
  octaves?: number
  slope?: number
  noiseOpacity?: number
}

/** SVG fractal grain. Overlay at low opacity with mix-blend-multiply. */
export function NoiseTexture({
  className,
  frequency = 0.65,
  octaves = 4,
  slope = 0.45,
  noiseOpacity = 0.55,
  ...props
}: NoiseTextureProps) {
  const filterId = useId()

  return (
    <svg
      aria-hidden
      className={cn('pointer-events-none absolute inset-0 size-full select-none', className)}
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      <filter id={filterId}>
        <feTurbulence
          type="fractalNoise"
          baseFrequency={frequency}
          numOctaves={octaves}
          stitchTiles="stitch"
        />
        <feColorMatrix type="saturate" values="0" />
        <feComponentTransfer>
          <feFuncR type="linear" slope={slope} />
          <feFuncG type="linear" slope={slope} />
          <feFuncB type="linear" slope={slope} />
        </feComponentTransfer>
      </filter>
      <rect width="100%" height="100%" filter={`url(#${filterId})`} opacity={noiseOpacity} />
    </svg>
  )
}
