import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { UploadDocument } from '../api/client'
import { useCreateClaim } from '../hooks/useClaims'
import type { DocumentType } from '../types/api'

interface DocumentSlot {
  id: string
  documentType: DocumentType
  file: File | null
}

let slotCounter = 0
function newSlot(documentType: DocumentType): DocumentSlot {
  slotCounter += 1
  return { id: `slot-${slotCounter}`, documentType, file: null }
}

export function UploadPage() {
  const navigate = useNavigate()
  const createClaim = useCreateClaim()
  const [hospitalCcn, setHospitalCcn] = useState('450123')
  const [slots, setSlots] = useState<DocumentSlot[]>([newSlot('BILL'), newSlot('EOB')])

  function updateSlot(id: string, patch: Partial<DocumentSlot>) {
    setSlots((prev) => prev.map((s) => (s.id === id ? { ...s, ...patch } : s)))
  }

  function addSlot() {
    setSlots((prev) => [...prev, newSlot('ITEMIZED_STATEMENT')])
  }

  function removeSlot(id: string) {
    setSlots((prev) => prev.filter((s) => s.id !== id))
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const documents: UploadDocument[] = slots
      .filter((s): s is DocumentSlot & { file: File } => s.file !== null)
      .map((s) => ({ file: s.file, documentType: s.documentType }))

    if (documents.length === 0) {
      return
    }

    const result = await createClaim.mutateAsync({ hospitalCcn, documents })
    navigate(`/claims/${result.claim_id}`)
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-semibold text-slate-900">Submit a claim for forensic audit</h1>
      <p className="mt-1 text-sm text-slate-500">
        Upload the itemized bill and EOB(s). EquiClaim will benchmark every line item against CMS
        price-transparency data, audit it against the No Surprises Act and NCCI rules, and produce
        a certified dispute docket for your review.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-6">
        <div>
          <label htmlFor="hospital_ccn" className="block text-sm font-medium text-slate-700">
            Hospital CMS Certification Number (CCN)
          </label>
          <input
            id="hospital_ccn"
            value={hospitalCcn}
            onChange={(e) => setHospitalCcn(e.target.value)}
            className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="e.g. 450123"
            required
          />
        </div>

        <div className="space-y-3">
          <span className="block text-sm font-medium text-slate-700">Documents</span>
          {slots.map((slot) => (
            <div key={slot.id} className="flex items-center gap-3 rounded-md border border-slate-200 p-3">
              <select
                value={slot.documentType}
                onChange={(e) => updateSlot(slot.id, { documentType: e.target.value as DocumentType })}
                className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              >
                <option value="BILL">Bill</option>
                <option value="EOB">EOB</option>
                <option value="ITEMIZED_STATEMENT">Itemized statement</option>
              </select>
              <input
                type="file"
                accept=".json,.txt"
                onChange={(e) => updateSlot(slot.id, { file: e.target.files?.[0] ?? null })}
                className="flex-1 text-sm"
              />
              <button
                type="button"
                onClick={() => removeSlot(slot.id)}
                className="text-sm text-slate-400 hover:text-red-600"
              >
                Remove
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={addSlot}
            className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
          >
            + Add another document
          </button>
        </div>

        {createClaim.isError && (
          <p className="text-sm text-red-600">
            Failed to submit claim: {(createClaim.error as Error).message}
          </p>
        )}

        <button
          type="submit"
          disabled={createClaim.isPending}
          className="w-full rounded-md bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
        >
          {createClaim.isPending ? 'Submitting…' : 'Start forensic audit'}
        </button>
      </form>
    </div>
  )
}
