// Mirrors app/schemas/api.py and app/schemas/*.py on the backend.
// Kept as a hand-written mirror (no codegen) since the backend contracts are
// small and stable; if they grow, generating this from the OpenAPI schema
// (already served at /openapi.json) would be the natural next step.

export type ClaimStatus =
  | 'INTAKE'
  | 'BENCHMARKING'
  | 'COMPLIANCE_REVIEW'
  | 'EVALUATING'
  | 'AWAITING_HUMAN_REVIEW'
  | 'RESUMING'
  | 'CERTIFIED'
  | 'REJECTED'
  | 'FAILED'

export type DocumentType = 'BILL' | 'EOB' | 'ITEMIZED_STATEMENT'

export type HumanDecision = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EDITED'

export interface ClaimCreateResponse {
  claim_id: string
  thread_id: string
  status: ClaimStatus
}

export interface ClaimStatusResponse {
  claim_id: string
  status: ClaimStatus
  eval_status: string | null
  eval_iteration: number | null
  next_nodes: string[]
  errors: string[]
  eval_feedback: string[]
  updated_at: string
}

export interface ClaimListItem {
  claim_id: string
  status: ClaimStatus
  hospital_ccn: string | null
  created_at: string
  updated_at: string
}

export interface ClaimListResponse {
  claims: ClaimListItem[]
}

export interface ResumeRequest {
  decision: 'APPROVED' | 'REJECTED'
  reviewer?: string
  notes?: string
}

export interface ClaimLineItem {
  line_item_id: string
  claim_id: string
  description: string
  cpt_hcpcs_code: string | null
  code_type: string | null
  units: number
  billed_amount_cents: number
  allowed_amount_cents: number | null
  patient_responsibility_cents: number | null
  service_date: string
  place_of_service: string | null
  is_emergency: boolean
  is_out_of_network: boolean | null
}

export interface DenialMapping {
  denial_id: string
  line_item_id: string
  carc_code: string
  carc_description: string
  rarc_code: string | null
  rarc_description: string | null
  group_code: 'CO' | 'PR' | 'OA' | 'PI'
  adjustment_amount_cents: number
}

export interface MRFBenchmark {
  benchmark_id: string
  hospital_ccn: string
  cpt_hcpcs_code: string
  code_type: string
  gross_charge_cents: number | null
  discounted_cash_cents: number | null
  median_negotiated_cents: number | null
  payer_count_sampled: number
  source_file_url: string
  source_publish_date: string
}

export interface ComplianceFinding {
  finding_id: string
  line_item_id: string
  rule_type: 'NSA_BALANCE_BILL_PROHIBITED' | 'NCCI_UNBUNDLING' | 'QPA_EXCEEDED' | 'MRF_PRICE_GOUGING'
  citation: string
  narrative: string
  disputed_amount_cents: number
  confidence: 'HIGH' | 'MEDIUM' | 'LOW'
}

export interface LineItemFinding {
  line_item: ClaimLineItem
  denial_mapping: DenialMapping | null
  mrf_benchmark: MRFBenchmark | null
  compliance_finding: ComplianceFinding | null
  disputed_amount_cents: number
}

export interface EvaluatorCertification {
  iteration_count: number
  passed_checks: string[]
  certified_at: string
}

export interface HumanApproval {
  decision: HumanDecision
  approved_by: string | null
  decided_at: string
  notes: string | null
}

export interface AuditDocket {
  docket_id: string
  claim_id: string
  generated_at: string
  line_item_findings: LineItemFinding[]
  total_billed_cents: number
  total_disputed_cents: number
  statutory_citations: string[]
  evaluator_certification: EvaluatorCertification
  human_approval: HumanApproval | null
  dispute_notice_text: string
}

export const TERMINAL_STATUSES: ClaimStatus[] = ['CERTIFIED', 'REJECTED', 'FAILED']
