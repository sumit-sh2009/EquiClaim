import { zodResolver } from '@hookform/resolvers/zod'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { ArrowLeft, ArrowRight, FileUp, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { apiErrorMessage, type UploadDocument } from '@/api/client'
import { useCreateClaim } from '@/hooks/useClaims'
import { auditIntakeSchema, MAX_AUDIT_FILE_BYTES, type AuditIntakeInput } from '@/lib/schemas'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { CcnCard } from '@/components/site/CcnCard'
import { ExhibitFrame } from '@/components/site/ExhibitFrame'
import { MagicCard } from '@/components/ui/magic-card'
import { SendButton } from '@/components/ui/send-button'
import { HardShadowButton } from '@/components/ui/hard-shadow-button'
import { TextAnimate } from '@/components/ui/text-animate'
import { TextReveal } from '@/components/ui/text-reveal'
import type { DocumentType } from '@/types/api'

const STEPS = ['Hospital', 'Documents', 'Review'] as const

interface DocSlot {
  type: DocumentType
  field: 'BILL' | 'EOB' | 'ITEMIZED_STATEMENT'
  label: string
  hint: string
  required: boolean
}

const DOC_SLOTS: DocSlot[] = [
  {
    type: 'BILL',
    field: 'BILL',
    label: 'Hospital bill',
    hint: 'Itemized hospital bill as .json or .txt.',
    required: true,
  },
  {
    type: 'EOB',
    field: 'EOB',
    label: 'Explanation of Benefits',
    hint: 'From your insurer — unlocks denial and allowed-amount analysis.',
    required: false,
  },
  {
    type: 'ITEMIZED_STATEMENT',
    field: 'ITEMIZED_STATEMENT',
    label: 'Itemized statement',
    hint: 'Optional supplement with additional line detail.',
    required: false,
  },
]

const ACCEPT = {
  'application/json': ['.json'],
  'text/plain': ['.txt'],
}

const SAMPLE_BILL_CONTENT = {
  line_items: [
    {
      ref: '1',
      description: 'Emergency department visit level 4',
      code: '99284',
      units: 1,
      billed_amount: 1500.0,
      service_date: '2026-01-15',
      place_of_service: '23',
      is_emergency: true,
      is_out_of_network: true,
    },
    {
      ref: '2',
      description: 'Routine venipuncture',
      code: '36415',
      units: 1,
      billed_amount: 45.0,
      service_date: '2026-01-15',
      place_of_service: '23',
      is_emergency: true,
      is_out_of_network: true,
    },
    {
      ref: '3',
      description: 'Chest X-ray, 2 views',
      code: '71046',
      units: 1,
      billed_amount: 180.0,
      service_date: '2026-01-15',
      place_of_service: '23',
    },
    {
      ref: '4',
      description: 'Chest X-ray, 1 view',
      code: '71045',
      units: 1,
      billed_amount: 110.0,
      service_date: '2026-01-15',
      place_of_service: '23',
    },
  ],
}

const SAMPLE_EOB_CONTENT = {
  line_items: [
    { ref: '1', allowed_amount: 320.0, patient_responsibility: 1180.0 },
    { ref: '2', allowed_amount: 8.0, patient_responsibility: 37.0 },
    { ref: '3', allowed_amount: 180.0, patient_responsibility: 0.0 },
    { ref: '4', allowed_amount: 110.0, patient_responsibility: 0.0 },
  ],
  denials: [
    {
      line_item_ref: '1',
      carc_code: '45',
      rarc_code: 'N822',
      group_code: 'CO',
      adjustment_amount: 0.0,
    },
  ],
}

export function UploadPage() {
  const [step, setStep] = useState(0)
  const createClaim = useCreateClaim()
  const navigate = useNavigate()
  const reduceMotion = useReducedMotion()
  const stepHeadingRef = useRef<HTMLHeadingElement>(null)

  const form = useForm<AuditIntakeInput>({
    resolver: zodResolver(auditIntakeSchema),
    defaultValues: {
      hospitalCcn: '',
      documents: {},
    },
    mode: 'onTouched',
  })

  const {
    control,
    register,
    handleSubmit,
    trigger,
    watch,
    setValue,
    clearErrors,
    formState: { errors },
  } = form

  const hospitalCcn = watch('hospitalCcn')
  const documents = watch('documents')

  useEffect(() => {
    stepHeadingRef.current?.focus()
  }, [step])

  function loadSampleData() {
    setValue('hospitalCcn', '450123', { shouldValidate: true, shouldDirty: true })
    const billFile = new File(
      [JSON.stringify(SAMPLE_BILL_CONTENT, null, 2)],
      'sample_bill.json',
      { type: 'application/json' },
    )
    const eobFile = new File(
      [JSON.stringify(SAMPLE_EOB_CONTENT, null, 2)],
      'sample_eob.json',
      { type: 'application/json' },
    )
    setValue('documents.BILL', billFile, { shouldValidate: true, shouldDirty: true })
    setValue('documents.EOB', eobFile, { shouldValidate: true, shouldDirty: true })
    toast.success('Loaded sample hospital paperwork', {
      description: 'Hospital CCN 450123, itemized bill, and insurer EOB attached.',
    })
    setStep(2)
  }

  async function goNext() {
    if (step === 0) {
      const ok = await trigger('hospitalCcn', { shouldFocus: true })
      if (!ok) return
      clearErrors()
      setStep(1)
      return
    }
    const ok = await trigger('documents.BILL', { shouldFocus: true, shouldTouch: true })
    if (ok) setStep(2)
  }

  function launch(values: AuditIntakeInput) {
    const parsed = auditIntakeSchema.parse(values)
    const uploads: UploadDocument[] = DOC_SLOTS.filter((s) => parsed.documents[s.field]).map((s) => ({
      file: parsed.documents[s.field] as File,
      documentType: s.type,
    }))
    createClaim.mutate(
      { hospitalCcn: parsed.hospitalCcn, documents: uploads },
      {
        onSuccess: (resp) => {
          toast.success('Audit started', {
            description: 'The pipeline is processing your documents.',
          })
          navigate(`/claims/${resp.claim_id}`)
        },
        onError: (err) => {
          toast.error('Could not start the audit', {
            description: apiErrorMessage(err, 'The audit service rejected the upload.'),
          })
        },
      },
    )
  }

  const ccnField = register('hospitalCcn')

  return (
    <div className="site-container section-pad max-w-4xl">
      <header>
        <TextReveal
          as="h1"
          play="mount"
          text="Start an audit"
          className="font-heading text-4xl tracking-tighter"
        />
        <p className="flow-sm text-sm leading-relaxed text-muted-foreground">
          Three short steps — we only ask for what the pipeline needs at each stage.
        </p>
      </header>

      <ol
        className="flow-lg grid grid-cols-3 gap-2 sm:gap-6"
        aria-label={`Step ${step + 1} of ${STEPS.length}: ${STEPS[step]}`}
      >
        {STEPS.map((label, i) => (
          <li
            key={label}
            aria-current={i === step ? 'step' : undefined}
            className={cn(
              'flex items-baseline gap-2 sm:gap-3 text-sm sm:text-2xl transition-colors',
              i === step ? 'text-foreground font-medium' : i < step ? 'text-emphasis' : 'text-muted-foreground',
            )}
          >
            <span
              className={cn(
                'font-mono text-xs sm:text-lg tracking-tight',
                i === step ? 'text-emphasis font-bold' : i < step ? 'text-emphasis' : undefined,
              )}
            >
              {String(i + 1).padStart(2, '0')}
            </span>
            <span className="font-heading tracking-tighter truncate">
              {label}
            </span>
          </li>
        ))}
      </ol>
      <div className="mt-5 h-1 w-full bg-border" aria-hidden>
        <div
          className="h-1 bg-foreground transition-[width] duration-300 ease-out"
          style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
        />
      </div>

      <ExhibitFrame kicker="Intake" className="mt-12 px-6 py-8 sm:px-8">
      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault()
          if (step < STEPS.length - 1) {
            void goNext()
            return
          }
          void handleSubmit(launch)(e)
        }}
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={step}
            initial={reduceMotion ? false : { opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={reduceMotion ? undefined : { opacity: 0, x: -24 }}
            transition={{ duration: 0.2, ease: [0.2, 0.6, 0.2, 1] }}
          >
            {step === 0 && (
              <section aria-labelledby="step-hospital">
                <h2
                  id="step-hospital"
                  ref={stepHeadingRef}
                  tabIndex={-1}
                  className="font-heading text-2xl font-medium tracking-tight outline-none"
                >
                  <TextAnimate as="span" by="word" animation="slideUp" duration={0.3}>
                    Which hospital issued the bill?
                  </TextAnimate>
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  The CMS certification number (CCN) lets us pull the hospital&rsquo;s published
                  price file for benchmarking.
                </p>
                <div className="flow-lg">
                  <CcnCard
                    id="hospital-ccn"
                    {...ccnField}
                    onChange={(e) => {
                      e.target.value = e.target.value.replace(/\D/g, '').slice(0, 10)
                      void ccnField.onChange(e)
                    }}
                    invalid={Boolean(errors.hospitalCcn)}
                    error={errors.hospitalCcn?.message}
                  />
                </div>
              </section>
            )}

            {step === 1 && (
              <section aria-labelledby="step-documents">
                <h2
                  id="step-documents"
                  ref={stepHeadingRef}
                  tabIndex={-1}
                  className="font-heading text-2xl font-medium tracking-tight outline-none"
                >
                  <TextAnimate as="span" by="word" animation="slideUp" duration={0.3}>
                    Add your documents
                  </TextAnimate>
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Only the bill is required. Each additional document sharpens the audit.
                </p>
                <div className="mt-6 flex flex-col">
                  {DOC_SLOTS.map((slot) => (
                    <Controller
                      key={slot.field}
                      control={control}
                      name={`documents.${slot.field}`}
                      render={({ field, fieldState }) => (
                        <FileDropRow
                          slot={slot}
                          file={field.value instanceof File ? field.value : undefined}
                          error={fieldState.error?.message}
                          onFile={field.onChange}
                          onClear={() => field.onChange(undefined)}
                        />
                      )}
                    />
                  ))}
                </div>
              </section>
            )}

            {step === 2 && (
              <section aria-labelledby="step-review">
                <h2
                  id="step-review"
                  ref={stepHeadingRef}
                  tabIndex={-1}
                  className="font-heading text-2xl font-medium tracking-tight outline-none"
                >
                  <TextAnimate as="span" by="word" animation="slideUp" duration={0.3}>
                    Review and launch
                  </TextAnimate>
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  The pipeline starts immediately and pauses for your review before anything is
                  filed.
                </p>
                <dl className="mt-6 text-sm">
                  <div className="flex justify-between gap-4 border-b border-dashed py-3">
                    <dt className="text-muted-foreground">Hospital CCN</dt>
                    <dd className="font-mono font-medium">{hospitalCcn?.trim()}</dd>
                  </div>
                  {DOC_SLOTS.filter((s) => documents?.[s.field] instanceof File).map((s) => (
                    <div
                      key={s.type}
                      className="flex items-center justify-between gap-4 border-b border-dashed py-3"
                    >
                      <dt className="text-muted-foreground">{s.label}</dt>
                      <dd className="max-w-56 truncate font-medium">
                        {(documents[s.field] as File).name}
                      </dd>
                    </div>
                  ))}
                </dl>
              </section>
            )}

            <div className="mt-10 flex flex-wrap items-center justify-between gap-4">
              {step > 0 ? (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setStep((s) => s - 1)}
                  disabled={createClaim.isPending}
                  className="gap-1.5 text-muted-foreground"
                >
                  <ArrowLeft data-icon="inline-start" aria-hidden />
                  Back
                </Button>
              ) : (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={loadSampleData}
                  className="gap-1.5 border-dashed text-xs"
                >
                  Load sample bill &amp; EOB
                </Button>
              )}
              {step < STEPS.length - 1 ? (
                <HardShadowButton type="submit" className="ml-auto">
                  Continue
                  <ArrowRight aria-hidden />
                </HardShadowButton>
              ) : (
                <SendButton
                  type="submit"
                  defaultLabel="Launch audit"
                  sentLabel="Launched"
                  sent={createClaim.isPending}
                  disabled={createClaim.isPending}
                />
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      </form>
      </ExhibitFrame>
    </div>
  )
}

function FileDropRow({
  slot,
  file,
  error,
  onFile,
  onClear,
}: {
  slot: DocSlot
  file: File | undefined
  error?: string
  onFile: (f: File) => void
  onClear: () => void
}) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted[0]) onFile(accepted[0])
    },
    [onFile],
  )

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    multiple: false,
    noClick: true,
    noKeyboard: true,
    maxSize: MAX_AUDIT_FILE_BYTES,
    accept: ACCEPT,
    onDropRejected: (rejections) => {
      const code = rejections[0]?.errors[0]?.code
      toast.error(
        code === 'file-too-large'
          ? 'That file is larger than 10 MB.'
          : code === 'file-invalid-type'
            ? 'Upload a .json or .txt file.'
            : `Could not attach the ${slot.label.toLowerCase()}.`,
      )
    },
  })

  return (
    <MagicCard
      className="rounded-none"
      gradientSize={180}
      gradientColor="var(--audit-glow)"
      gradientFrom="var(--audit)"
      gradientTo="transparent"
    >
      <div
        {...getRootProps({
          className: cn(
            'flex items-center gap-4 border-b border-dashed py-4 transition-colors',
            isDragActive && 'bg-accent',
          ),
        })}
      >
        <input {...getInputProps({ 'aria-label': `Upload ${slot.label}` })} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">
            {slot.label}
            {slot.required ? (
              <>
                <span className="ml-1 text-destructive" aria-hidden>
                  *
                </span>
                <span className="sr-only">(required)</span>
              </>
            ) : (
              <span className="ml-2 text-xs font-normal text-muted-foreground">optional</span>
            )}
          </p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {file ? file.name : isDragActive ? 'Drop the file here' : slot.hint}
          </p>
          {error && (
            <p role="alert" className="mt-1 text-xs text-destructive">
              {error}
            </p>
          )}
        </div>
        {file ? (
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={(e) => {
              e.stopPropagation()
              onClear()
            }}
            aria-label={`Remove ${slot.label}`}
          >
            <X aria-hidden />
          </Button>
        ) : (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation()
              open()
            }}
            className="gap-1.5 rounded-full bg-card"
          >
            <FileUp data-icon="inline-start" aria-hidden />
            Choose file
          </Button>
        )}
      </div>
    </MagicCard>
  )
}
