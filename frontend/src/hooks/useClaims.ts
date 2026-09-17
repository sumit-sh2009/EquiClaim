import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createClaim, getClaimStatus, getDocket, listClaims, resumeClaim } from '../api/client'
import type { UploadDocument } from '../api/client'
import type { ResumeRequest } from '../types/api'
import { TERMINAL_STATUSES } from '../types/api'

const POLL_INTERVAL_MS = 2500

/** Claim ledger — polls continuously; the list as a whole is never "terminal". */
export function useClaimList() {
  return useQuery({
    queryKey: ['claims'],
    queryFn: listClaims,
    refetchInterval: POLL_INTERVAL_MS,
  })
}

/**
 * Single-claim status polling that backs off once the claim reaches a
 * terminal status (CERTIFIED/REJECTED/FAILED) — matches the blueprint's
 * "polling with backoff once terminal" requirement.
 */
export function useClaimStatus(claimId: string | undefined) {
  return useQuery({
    queryKey: ['claims', claimId, 'status'],
    queryFn: () => getClaimStatus(claimId as string),
    enabled: Boolean(claimId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status && TERMINAL_STATUSES.includes(status)) {
        return false
      }
      return POLL_INTERVAL_MS
    },
  })
}

export function useDocket(claimId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['claims', claimId, 'docket'],
    queryFn: () => getDocket(claimId as string),
    enabled: Boolean(claimId) && enabled,
  })
}

export function useCreateClaim() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (params: { hospitalCcn: string; documents: UploadDocument[] }) =>
      createClaim(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claims'] })
    },
  })
}

export function useResumeClaim(claimId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ResumeRequest) => resumeClaim(claimId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claims', claimId, 'status'] })
      queryClient.invalidateQueries({ queryKey: ['claims'] })
    },
  })
}
