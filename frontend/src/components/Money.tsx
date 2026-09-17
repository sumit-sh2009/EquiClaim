export function formatCents(cents: number): string {
  return (cents / 100).toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

export function Money({ cents, className }: { cents: number; className?: string }) {
  return <span className={className}>{formatCents(cents)}</span>
}
