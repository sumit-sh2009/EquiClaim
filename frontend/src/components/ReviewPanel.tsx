import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { apiErrorMessage } from '@/api/client'
import { useResumeClaim } from '@/hooks/useClaims'
import { reviewDecisionSchema, type ReviewDecision } from '@/lib/schemas'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { MagicCard } from '@/components/ui/magic-card'
import { SendButton } from '@/components/ui/send-button'
import { HardShadowButton } from '@/components/ui/hard-shadow-button'
import { Textarea } from '@/components/ui/textarea'

/**
 * The human-in-the-loop decision surface. Visually quiet until acted on:
 * a warning keyline, the two fields the audit trail needs, and two clearly
 * prioritized actions behind explicit confirmations.
 */
export function ReviewPanel({ claimId }: { claimId: string }) {
  const resume = useResumeClaim(claimId)
  const [pendingDecision, setPendingDecision] = useState<'APPROVED' | 'REJECTED' | null>(null)

  const {
    register,
    trigger,
    getValues,
    watch,
    formState: { errors },
  } = useForm<ReviewDecision>({
    resolver: zodResolver(reviewDecisionSchema),
    defaultValues: { reviewer: '', notes: '' },
    mode: 'onTouched',
  })

  const reviewer = watch('reviewer')

  async function requestDecision(decision: 'APPROVED' | 'REJECTED') {
    const ok = await trigger(undefined, { shouldFocus: true })
    if (!ok) return
    setPendingDecision(decision)
  }

  function confirm(decision: 'APPROVED' | 'REJECTED') {
    const { reviewer, notes } = getValues()
    resume.mutate(
      { decision, reviewer: reviewer || undefined, notes: notes || undefined },
      {
        onSuccess: () =>
          toast.success(
            decision === 'APPROVED' ? 'Docket certified and filed' : 'Docket rejected and archived',
          ),
        onError: (err) =>
          toast.error('Resume failed', {
            description: apiErrorMessage(err, 'The audit service could not record this decision.'),
          }),
      },
    )
    setPendingDecision(null)
  }

  return (
    <MagicCard
      className="rounded-lg"
      gradientSize={220}
      gradientColor="color-mix(in oklch, var(--warning) 7%, transparent)"
      gradientFrom="color-mix(in oklch, var(--warning) 40%, transparent)"
      gradientTo="color-mix(in oklch, var(--warning) 22%, transparent)"
    >
      <section
        aria-labelledby="review-heading"
        className="rounded-[inherit] bg-warning/[0.06] px-6 py-5"
      >
        <div className="flex items-center gap-2">
          <span aria-hidden className="size-1.5 rounded-full bg-warning" />
          <h2 id="review-heading" className="font-medium">
            This docket is waiting on you
          </h2>
        </div>
        <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-muted-foreground">
          The evaluator certified the findings below. Approve to finalize the dispute, or reject to
          archive the claim — either way it&rsquo;s recorded in the audit trail.
        </p>

        <FieldGroup className="mt-5 sm:grid sm:grid-cols-2">
          <Field data-invalid={errors.reviewer ? true : undefined}>
            <FieldLabel htmlFor="reviewer">Reviewer</FieldLabel>
            <Input
              id="reviewer"
              {...register('reviewer')}
              placeholder="you@example.com"
              autoComplete="email"
              aria-invalid={errors.reviewer ? true : undefined}
              className="bg-card"
            />
            <FieldError errors={[errors.reviewer]} />
          </Field>
          <Field data-invalid={errors.notes ? true : undefined}>
            <FieldLabel htmlFor="review-notes">Notes (optional)</FieldLabel>
            <Textarea
              id="review-notes"
              {...register('notes')}
              placeholder="Context for the audit trail"
              aria-invalid={errors.notes ? true : undefined}
              className="min-h-10 bg-card"
            />
            <FieldError errors={[errors.notes]} />
          </Field>
        </FieldGroup>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <HardShadowButton
            type="button"
            disabled={resume.isPending}
            onClick={() => void requestDecision('APPROVED')}
            className="hard-shadow-btn--compact"
          >
            Approve &amp; file dispute
          </HardShadowButton>
          <HardShadowButton
            type="button"
            tone="paper"
            disabled={resume.isPending}
            onClick={() => void requestDecision('REJECTED')}
            className="hard-shadow-btn--compact"
          >
            Reject
          </HardShadowButton>
        </div>

        <AlertDialog
          open={pendingDecision !== null}
          onOpenChange={(open) => !open && setPendingDecision(null)}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>
                {pendingDecision === 'APPROVED' ? 'File this dispute?' : 'Reject this docket?'}
              </AlertDialogTitle>
              <AlertDialogDescription>
                {pendingDecision === 'APPROVED'
                  ? `The certified docket and formal dispute notice will be finalized for this claim. This is recorded in the audit trail${reviewer ? ` under ${reviewer}` : ''}.`
                  : 'The claim will be archived without filing a dispute. You can start a new audit at any time.'}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter className="flex-col gap-3 sm:flex-row sm:items-center">
              <AlertDialogCancel>Keep reviewing</AlertDialogCancel>
              {pendingDecision === 'APPROVED' ? (
                <SendButton
                  type="button"
                  defaultLabel="Approve & file"
                  sentLabel="Filed"
                  sent={resume.isPending}
                  disabled={resume.isPending}
                  onClick={() => confirm('APPROVED')}
                />
              ) : (
                <AlertDialogAction onClick={() => confirm('REJECTED')}>
                  Reject docket
                </AlertDialogAction>
              )}
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </section>
    </MagicCard>
  )
}
