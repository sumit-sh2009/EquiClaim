import axios from 'axios'
import type {
  AuditDocket,
  ClaimCreateResponse,
  ClaimListResponse,
  ClaimStatusResponse,
  DocumentType,
  ResumeRequest,
} from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const BEARER_TOKEN = import.meta.env.VITE_API_BEARER_TOKEN ?? 'dev-shared-secret-change-me'
const TENANT_ID = import.meta.env.VITE_TENANT_ID ?? 'demo-tenant'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    Authorization: `Bearer ${BEARER_TOKEN}`,
    'X-Tenant-Id': TENANT_ID,
  },
})

export interface UploadDocument {
  file: File
  documentType: DocumentType
}

export async function createClaim(params: {
  hospitalCcn: string
  documents: UploadDocument[]
}): Promise<ClaimCreateResponse> {
  const formData = new FormData()
  formData.append('hospital_ccn', params.hospitalCcn)
  for (const doc of params.documents) {
    formData.append('files', doc.file)
    formData.append('document_types', doc.documentType)
  }
  const { data } = await apiClient.post<ClaimCreateResponse>('/claims', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function listClaims(): Promise<ClaimListResponse> {
  const { data } = await apiClient.get<ClaimListResponse>('/claims')
  return data
}

export async function getClaimStatus(claimId: string): Promise<ClaimStatusResponse> {
  const { data } = await apiClient.get<ClaimStatusResponse>(`/claims/${claimId}/status`)
  return data
}

export async function resumeClaim(
  claimId: string,
  body: ResumeRequest,
): Promise<ClaimStatusResponse> {
  const { data } = await apiClient.post<ClaimStatusResponse>(`/claims/${claimId}/resume`, body)
  return data
}

export async function getDocket(claimId: string): Promise<AuditDocket> {
  const { data } = await apiClient.get<AuditDocket>(`/claims/${claimId}/docket`)
  return data
}
