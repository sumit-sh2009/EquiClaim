import { z } from 'zod'

/** CMS CCN on the bill header is 6 digits; some systems pad to 10. */
export const hospitalCcnSchema = z
  .string()
  .trim()
  .regex(/^\d{6,10}$/, { error: 'Enter the 6–10 digit CMS certification number.' })

export const MAX_AUDIT_FILE_BYTES = 10_000_000

const auditFile = z
  .file()
  .max(MAX_AUDIT_FILE_BYTES, {
    error: 'Files must be 10 MB or smaller.',
  })
  .refine((file) => /\.(json|txt)$/i.test(file.name), {
    error: 'Upload a .json or .txt file.',
  })

export const auditIntakeSchema = z.object({
  hospitalCcn: hospitalCcnSchema,
  documents: z.object({
    BILL: z
      .file({ error: 'Attach the hospital bill.' })
      .max(MAX_AUDIT_FILE_BYTES, { error: 'Files must be 10 MB or smaller.' })
      .refine((file) => /\.(json|txt)$/i.test(file.name), {
        error: 'Upload a .json or .txt file.',
      }),
    EOB: auditFile.optional(),
    ITEMIZED_STATEMENT: auditFile.optional(),
  }),
})

export type AuditIntake = z.infer<typeof auditIntakeSchema>
export type AuditIntakeInput = z.input<typeof auditIntakeSchema>

export const reviewDecisionSchema = z.object({
  reviewer: z.union([
    z.literal(''),
    z.email({ error: 'Enter a valid email, or leave it blank.' }),
  ]),
  notes: z
    .string()
    .max(2000, { error: 'Notes must be 2,000 characters or fewer.' })
    .optional(),
})

export type ReviewDecision = z.infer<typeof reviewDecisionSchema>
