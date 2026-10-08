import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import {
  CertificationTrail,
  DocketFindings,
  DocketNotice,
  DocketSummary,
} from '@/components/DocketViewer'
import { ReviewPanel } from '@/components/ReviewPanel'
import { ExhibitFrame } from '@/components/site/ExhibitFrame'
import { StatusBadge } from '@/components/StatusBadge'
import { useClaimStatus, useDocket } from '@/hooks/useClaims'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { ScrollProgress } from '@/components/ui/scroll-progress'
import { SpeederLoader } from '@/components/ui/speeder-loader'

/**
 * A claim page reads top-to-bottom like the docket it produces:
 * the money first, then the evidence, then the paper trail.
 */
export function ClaimDetailPage() {
  const { claimId } = useParams<{ claimId: string }>()
  const { data: status, isLoading, isError, refetch } = useClaimStatus(claimId)
  const showDocket =
    status?.status === 'AWAITING_HUMAN_REVIEW' ||
    status?.status === 'CERTIFIED' ||
    status?.status === 'REJECTED'
  const { data: docket } = useDocket(claimId, showDocket)

  return (
    <div className="site-container section-pad max-w-4xl">
      <ScrollProgress />
      <Link
        to="/claims"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden />
        Ledger
      </Link>

      <div className="flow-sm flex flex-wrap items-baseline justify-between gap-4">
        <h1 className="font-mono text-base sm:text-lg font-medium tracking-tight break-all">{claimId}</h1>
        {status && <StatusBadge status={status.status} />}
      </div>

      {isLoading && <SpeederLoader label="Loading claim" className="mt-10 min-h-48" />}

      {isError && (
        <div role="alert" className="mt-10 border-t py-12 text-center">
          <p className="font-medium">This claim couldn&rsquo;t be loaded</p>
          <p className="mt-1 text-sm text-muted-foreground">
            The audit service may be unreachable, or the claim ID is wrong.
          </p>
          <Button variant="outline" className="mt-4" onClick={() => refetch()}>
            Try again
          </Button>
        </div>
      )}

      {status && (
        <div className="mt-8 flex flex-col gap-12">
          {status.status === 'FAILED' && (
            <Alert variant="destructive">
              <AlertTitle>Escalated for manual review</AlertTitle>
              <AlertDescription>
                The automated pipeline couldn&rsquo;t certify this claim within its iteration
                limit, so it was routed out of the graph for a human to handle directly.
              </AlertDescription>
            </Alert>
          )}

          {status.status === 'AWAITING_HUMAN_REVIEW' && claimId && (
            <ReviewPanel claimId={claimId} />
          )}

          {docket && (
            <>
              <section aria-labelledby="docket-summary">
                <h2 id="docket-summary" className="sr-only">
                  Financial summary
                </h2>
                <DocketSummary docket={docket} />
              </section>

              <section aria-labelledby="docket-findings" className="pt-4">
                <h2 id="docket-findings" className="sr-only">
                  Findings
                </h2>
                <ExhibitFrame kicker="Findings" className="px-2 py-4 sm:px-4">
                  <DocketFindings docket={docket} />
                </ExhibitFrame>
              </section>

              <section aria-labelledby="docket-notice">
                <h2
                  id="docket-notice"
                  className="border-t pt-8 font-heading text-2xl font-medium tracking-tight"
                >
                  Dispute notice
                </h2>
                <div className="mt-6">
                  <DocketNotice docket={docket} />
                </div>
              </section>

              <section aria-labelledby="docket-certification" className="pt-4">
                <h2 id="docket-certification" className="sr-only">
                  Certification
                </h2>
                <ExhibitFrame kicker="Certification" className="px-6 py-6">
                  <CertificationTrail docket={docket} />
                </ExhibitFrame>
              </section>
            </>
          )}

          {status.eval_feedback.length > 0 && (
            <Accordion>
              <AccordionItem value="feedback" className="border-t">
                <AccordionTrigger className="text-sm">
                  Evaluator feedback history ({status.eval_feedback.length})
                </AccordionTrigger>
                <AccordionContent>
                  <ul className="flex flex-col gap-2 pb-2">
                    {status.eval_feedback.map((fb, i) => (
                      <li
                        key={i}
                        className="border-l-2 border-destructive/40 py-1 pl-3 font-mono text-xs leading-relaxed text-muted-foreground"
                      >
                        {fb}
                      </li>
                    ))}
                  </ul>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          )}
        </div>
      )}
    </div>
  )
}
