import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-xl border-2 border-border bg-clip-padding text-sm font-medium whitespace-nowrap transition-all outline-none select-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow-[4px_4px_0_0_var(--border)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none active:translate-y-1",
        outline:
          "bg-card text-foreground shadow-[4px_4px_0_0_var(--border)] hover:translate-x-[2px] hover:translate-y-[2px] hover:bg-accent hover:text-accent-foreground hover:shadow-none",
        secondary:
          "bg-secondary text-secondary-foreground shadow-[4px_4px_0_0_var(--border)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none",
        ghost:
          "border-transparent shadow-none hover:bg-accent hover:text-accent-foreground hover:border-border",
        destructive:
          "bg-destructive text-destructive-foreground shadow-[4px_4px_0_0_var(--border)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none",
        link: "border-transparent shadow-none text-foreground underline-offset-4 hover:underline",
      },
      size: {
        default:
          "h-8 gap-1.5 px-3 has-data-[icon=inline-end]:pr-2.5 has-data-[icon=inline-start]:pl-2.5",
        xs: "h-6 gap-1 px-2.5 text-xs has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-7 gap-1 px-3 text-[0.8rem] has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-11 gap-2 px-6 text-[0.95rem] has-data-[icon=inline-end]:pr-5 has-data-[icon=inline-start]:pl-5",
        icon: "size-8",
        "icon-xs": "size-6 [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-7",
        "icon-lg": "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
