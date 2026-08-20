// InventorySync.tsx — Inventory Sync
//
// Phase 3, Sprint 4: wired to the real upload-triggered sync workflow
// (POST /inventory-sync/run) plus three read endpoints (GET /dashboard's
// connected_systems, GET /inventory-sync/history, GET /inventory-sync/exceptions).
// Previously this entire page was inline mock arrays with no backend
// integration and no working "Run Sync Now" handler at all.
//
// Per this sprint's own instruction, the mockup's layout is preserved,
// not redesigned -- data sources are swapped, and where the mockup shows
// something the backend has no equivalent for, that's rendered honestly
// instead of fabricated:
// - The mockup's "Sync Run Selector" (fixed "7:02 AM" / "12:31 PM" tabs,
//   each with a pre-baked exceptions/tasks snapshot) assumed a per-run
//   history richer than what SyncRun actually stores (see
//   queries/inventory_sync.py's sync_run_history docstring for why
//   per-batch task/recommendation/exception counts aren't reconstructed
//   retroactively). Replaced with a real "Recent Sync Runs" list showing
//   what a batch of SyncRun rows actually carries -- sources, status,
//   records processed -- not fake per-run stats.
// - The mockup's Exceptions table had an assignable status/suggestedAction
//   workflow (Under Review, Task Created, ...) with no backend behind it
//   at all. Replaced with real, persisted PendingIdentity rows
//   (raw_identifier, identifier_type, first/last observed) -- the
//   Exceptions panel's actual backend equivalent, per
//   FRONTEND_BACKEND_RECONCILIATION.md's already-documented gap.
// - The Stats Bar / "Detected Changes" panel reflect the most recent
//   sync run *in this browser session* (SyncSummaryDTO's own fields --
//   vehicles_processed, exceptions_found, tasks_generated,
//   recommendations_generated) -- not persisted, not reconstructed after
//   a reload, exactly like every other ephemeral summary state in this
//   app.
//
// Sprint 10 (Rail D, Inventory Ingestion Safety): the single-shot
// upload flow became validate -> preview -> (acknowledge) -> run:
// - "Validate Reports" calls POST /inventory-sync/validate (zero
//   mutation server-side) and renders a per-report preview: detected
//   type, row counts, duplicates, prior-comparable-baseline change,
//   and every issue at its severity.
// - Selecting/changing any file invalidates the preview immediately;
//   the server would reject a stale fingerprint anyway
//   (STALE_VALIDATION) -- the UI just doesn't pretend otherwise.
// - Warnings require the operator to tick an acknowledgement box that
//   is NEVER pre-checked. The run request carries the acknowledgement
//   plus the validation fingerprint; the server revalidates everything
//   itself, so this UI is UX, not the safety boundary.
// - "Run Sync Now" stays disabled until a current validation exists
//   with no errors and (if warnings) the acknowledgement is ticked.

import { useMemo, useState } from 'react'
import { track } from '../observability/analytics'
import { getExceptions, getSyncHistory, runInventorySync, validateInventoryReports } from '../api/inventorySync'
import { useApi } from '../api/useApi'
import { useDashboardData } from '../api/dashboardData'
import { ApiError, isBackendUnavailable, ValidationRejectedError } from '../api/client'
import type { InventorySyncFiles } from '../api/inventorySync'
import type {
  IngestionIssueDTO, IngestionValidationDTO, PendingIdentityDTO,
  ReportValidationDTO, SyncSummaryDTO,
} from '../api/types'

const UPLOAD_SLOTS: { field: keyof InventorySyncFiles; label: string }[] = [
  { field: 'tekion_unsold', label: 'Tekion Unsold Inventory' },
  { field: 'tekion_sold', label: 'Tekion Sold Inventory' },
  { field: 'keyper', label: 'Keyper' },
  { field: 'mdd', label: 'MDD' },
  { field: 'recovr', label: 'RecovR' },
  { field: 'rapidrecon', label: 'RapidRecon' },
]

// Sprint 12 (audit D4, Phase 6): PendingIdentity's identifier_type is
// a backend classification code (sync/normalizer.py), not display
// copy. Translate to dealership-operational language at render; the
// raw code stays in the row's title attribute for debugging and in
// telemetry, where codes -- never contents -- are the contract.
const EXCEPTION_REASON_LABELS: Record<string, string> = {
  unrecognized: "Key name doesn't match any known vehicle identifier format",
  tekion_auto_generated_stock_number: 'Numeric key name looks like an auto-generated Tekion stock number — no matching vehicle',
  last6_vin: 'Matches the last 6 digits of a VIN, but no current vehicle carries it',
  ambiguous_last6_vin_multiple_matches: 'Last-6 VIN digits match more than one vehicle — needs a person to resolve',
  stock_number: 'Stock-number-style key name with no matching vehicle in inventory',
  non_vehicle: 'Recognized non-vehicle key (facility or loaner key)',
}

function exceptionReason(identifierType: string): string {
  return EXCEPTION_REASON_LABELS[identifierType]
    ?? identifierType.replace(/_/g, ' ')
}

// Decorative -- adjacent text carries the status meaning.
function SystemDot({ status }: { status: string }) {
  if (status === 'complete')
    return <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
  if (status === 'in_progress' || status === 'delayed')
    return <span className="inline-block w-2 h-2 rounded-full bg-amber-400 shrink-0" />
  if (status === 'failed')
    return <span className="inline-block w-2 h-2 rounded-full bg-red-500 shrink-0" />
  return <span className="inline-block w-2 h-2 rounded-full bg-slate-300 shrink-0" />
}

function statusLabel(status: string): string {
  switch (status) {
    case 'complete': return 'Connected'
    case 'in_progress': return 'Running'
    case 'delayed': return 'Delayed'
    case 'failed': return 'Failed'
    default: return status
  }
}

// Source keys are stored lowercase (sync_run.source); these are real
// product/brand names, so a generic `capitalize` mangles three of the
// five ("Mdd", "Recovr", "Rapidrecon").
const SOURCE_LABEL: Record<string, string> = {
  tekion: 'Tekion', keyper: 'Keyper', mdd: 'MDD', recovr: 'RecovR', rapidrecon: 'RapidRecon',
}
function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="15" height="15" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M13.65 2.35A8 8 0 1 0 15 8h-2a6 6 0 1 1-1.76-4.24L9 6h6V0l-1.35 2.35Z" fill="currentColor" />
    </svg>
  )
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="15" height="15" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 11V3M8 3L4.5 6.5M8 3l3.5 3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M2.5 12.5v1a1 1 0 001 1h9a1 1 0 001-1v-1" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="13" height="13" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.3" />
      <path d="M9.5 9.5L12.5 12.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  )
}

function TaskIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="13" height="13" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1.5" y="1.5" width="11" height="11" rx="2" stroke="currentColor" strokeWidth="1.3" />
      <path d="M4 7h6M4 4.5h6M4 9.5h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  )
}

function LightbulbIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="13" height="13" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M7 1a4 4 0 0 0-2 7.46V10h4V8.46A4 4 0 0 0 7 1Z" stroke="currentColor" strokeWidth="1.3" />
      <path d="M5 10h4M5.5 12h3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  )
}

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="13" height="13" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M7 1.5L13 12.5H1L7 1.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
      <path d="M7 5.5v3M7 10.5v.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  )
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="13" height="13" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2.5 7.5L5.5 10.5L11.5 3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function CrossIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="13" height="13" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M3.5 3.5L10.5 10.5M10.5 3.5L3.5 10.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

function InfoIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="13" height="13" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.3" />
      <path d="M7 6.5v3.5M7 4v.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  )
}

const spinner = (
  <svg width="14" height="14" fill="none" viewBox="0 0 24 24" className="animate-spin">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.2" />
    <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
  </svg>
)

function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

function IssueLine({ issue }: { issue: IngestionIssueDTO }) {
  const style = issue.severity === 'error'
    ? { box: 'bg-red-50 border-red-100 text-red-700', icon: <CrossIcon className="text-red-500 mt-0.5 shrink-0" /> }
    : issue.severity === 'warning'
      ? { box: 'bg-amber-50 border-amber-100 text-amber-800', icon: <WarningIcon className="text-amber-500 mt-0.5 shrink-0" /> }
      : { box: 'bg-slate-50 border-slate-100 text-slate-600', icon: <InfoIcon className="text-slate-400 mt-0.5 shrink-0" /> }
  return (
    <div className={`flex items-start gap-2 border rounded-lg px-2.5 py-2 text-[12px] leading-snug ${style.box}`}>
      {style.icon}
      <span>{issue.message}</span>
    </div>
  )
}

function ReportPreviewCard({ report }: { report: ReportValidationDTO }) {
  const status = report.status === 'ready'
    ? { chip: 'bg-emerald-50 text-emerald-700', icon: <CheckIcon className="text-emerald-500" />, label: 'Ready' }
    : report.status === 'needs_review'
      ? { chip: 'bg-amber-50 text-amber-700', icon: <WarningIcon className="text-amber-500" />, label: 'Review needed' }
      : { chip: 'bg-red-50 text-red-700', icon: <CrossIcon className="text-red-500" />, label: 'Rejected' }

  const baseline = report.baseline
  const showStats = report.detected !== null && report.status !== 'rejected'

  return (
    <div className="border border-slate-100 rounded-xl p-3.5 flex flex-col gap-2.5 bg-white">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[13px] font-semibold text-slate-800">{report.slot_label}</span>
        <span className={`flex items-center gap-1.5 text-[11px] font-semibold px-2 py-0.5 rounded-full ${status.chip}`}>
          {status.icon}
          {status.label}
        </span>
      </div>

      <div className="text-[12px] text-slate-500">
        Detected:{' '}
        {report.detected ? (
          <span className="text-slate-700 font-medium">
            {report.detected.vendor} — {report.detected.report_type}
          </span>
        ) : (
          <span className="text-slate-400">not recognized</span>
        )}
      </div>

      {showStats && (
        <div className="grid grid-cols-4 gap-2 text-center">
          {[
            { label: 'Records', value: report.stats.total_rows },
            { label: 'Valid', value: report.stats.valid_rows },
            { label: 'Invalid', value: report.stats.invalid_rows },
            { label: 'Duplicates', value: report.stats.duplicate_rows + report.stats.duplicate_identifiers },
          ].map(s => (
            <div key={s.label} className="bg-slate-50 rounded-lg py-1.5">
              <div className="text-[14px] font-bold text-slate-800 leading-tight">{s.value.toLocaleString()}</div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wide">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {showStats && baseline && (
        <div className="text-[12px] text-slate-500">
          {baseline.previous_rows === null ? (
            <span>No prior comparable report to compare against.</span>
          ) : (
            <span>
              Previous comparable: <span className="font-medium text-slate-700">{baseline.previous_rows.toLocaleString()}</span>
              {baseline.change !== null && (
                <>
                  {' '}· Change:{' '}
                  <span className={`font-medium ${(baseline.change ?? 0) < 0 ? 'text-amber-700' : 'text-slate-700'}`}>
                    {(baseline.change ?? 0) >= 0 ? '+' : ''}{baseline.change?.toLocaleString()}
                    {baseline.change_pct !== null && ` (${(baseline.change_pct ?? 0) >= 0 ? '+' : ''}${baseline.change_pct}%)`}
                  </span>
                </>
              )}
            </span>
          )}
        </div>
      )}

      {report.issues.length > 0 && (
        <div className="flex flex-col gap-1.5">
          {report.issues.map((issue, i) => (
            <IssueLine key={`${issue.code}-${i}`} issue={issue} />
          ))}
        </div>
      )}
    </div>
  )
}

type RunState =
  | { status: 'idle' }
  | { status: 'running' }
  | { status: 'error'; message: string }
  | { status: 'success'; summary: SyncSummaryDTO }

type ValidationState =
  | { status: 'idle' }
  | { status: 'validating' }
  | { status: 'done'; result: IngestionValidationDTO; note?: string }
  | { status: 'error'; message: string }

// Sprint 11 (analytics): validation outcome events fire on the
// OBSERVED SERVER RESPONSE -- the DTO in hand IS the server's verdict
// (client-vs-server authority rule, OBSERVABILITY.md). Safe properties
// only: slots, issue codes, aggregate counts. Never filenames, VINs,
// or report contents.
function trackValidationOutcome(result: IngestionValidationDTO) {
  const event =
    result.status === 'rejected' ? 'inventory_validation_blocked'
    : result.status === 'needs_review' ? 'inventory_validation_warning'
    : 'inventory_validation_completed'
  track(event, {
    slots: result.reports.map(r => r.slot),
    codes: [...new Set(result.reports.flatMap(r => r.issues.map(i => i.code)))],
    total_rows: result.reports.reduce((n, r) => n + r.stats.total_rows, 0),
    valid_rows: result.reports.reduce((n, r) => n + r.stats.valid_rows, 0),
  })
}

export default function InventorySync(): JSX.Element {
  const [search, setSearch] = useState('')
  const [files, setFiles] = useState<InventorySyncFiles>({})
  const [runState, setRunState] = useState<RunState>({ status: 'idle' })
  const [validation, setValidation] = useState<ValidationState>({ status: 'idle' })
  const [ack, setAck] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  // Sprint 14 (Rail J): the connected-systems panel reads the shared
  // per-view /dashboard fetch; after a completed run handleRunSync
  // calls refreshDashboard() alongside the page's own refreshKey.
  const { state: dashboardState, refresh: refreshDashboard } = useDashboardData(true)
  const historyState = useApi(() => getSyncHistory(), [refreshKey])
  const exceptionsState = useApi(() => getExceptions(), [refreshKey])

  const connectedSystems = dashboardState.status === 'success' ? dashboardState.data.connected_systems : {}
  const history = historyState.status === 'success' ? historyState.data : []
  const exceptions: PendingIdentityDTO[] = exceptionsState.status === 'success' ? exceptionsState.data : []

  const filteredExceptions = useMemo(() => {
    if (!search.trim()) return exceptions
    const q = search.toLowerCase()
    return exceptions.filter(
      e =>
        e.raw_identifier.toLowerCase().includes(q) ||
        e.identifier_type.toLowerCase().includes(q) ||
        exceptionReason(e.identifier_type).toLowerCase().includes(q) ||
        e.source.toLowerCase().includes(q),
    )
  }, [exceptions, search])

  const selectedCount = Object.values(files).filter(Boolean).length
  const summary = runState.status === 'success' ? runState.summary : null

  // The run gate, mirrored from the server's own rules (which are the
  // real boundary -- the server revalidates and would reject anyway):
  // a current validation, no errors, and warnings acknowledged.
  const canRun =
    validation.status === 'done' &&
    validation.result.status !== 'rejected' &&
    (!validation.result.requires_acknowledgement || ack)

  const handleFileChange = (field: keyof InventorySyncFiles, file: File | undefined) => {
    setFiles(prev => ({ ...prev, [field]: file }))
    // Any file change invalidates the preview (Sprint 10 phase 20) --
    // the acknowledgement box resets with it, never surviving a file
    // swap.
    setValidation({ status: 'idle' })
    setAck(false)
    if (runState.status === 'error') setRunState({ status: 'idle' })
  }

  const handleValidate = async () => {
    if (selectedCount === 0 || validation.status === 'validating') return
    setValidation({ status: 'validating' })
    setAck(false)
    try {
      const result = await validateInventoryReports(files)
      setValidation({ status: 'done', result })
      trackValidationOutcome(result)
    } catch (err) {
      setValidation({
        status: 'error',
        message: err instanceof Error ? err.message : 'Unexpected error',
      })
    }
  }

  const handleRunSync = async () => {
    if (!canRun || runState.status === 'running' || validation.status !== 'done') return
    setRunState({ status: 'running' })
    // USER INTENT event (the click); completion below is the observed
    // server outcome -- deliberately separate authorities.
    track('inventory_sync_started', {
      slots: Object.entries(files).filter(([, f]) => f).map(([slot]) => slot),
      warnings_acknowledged: ack,
    })
    try {
      const result = await runInventorySync(files, {
        acknowledgeWarnings: ack,
        validationFingerprint: validation.result.fingerprint,
      })
      track('inventory_sync_completed', {
        sources: result.sync_runs.map(r => r.source),
        vehicles_processed: result.vehicles_processed,
        tasks_generated: result.tasks_generated,
        recommendations_generated: result.recommendations_generated,
      })
      setRunState({ status: 'success', summary: result })
      setFiles({})
      setValidation({ status: 'idle' })
      setAck(false)
      setRefreshKey(k => k + 1)
      refreshDashboard()
    } catch (err) {
      if (err instanceof ApiError && err.status >= 500) {
        track('inventory_sync_failed', { status: err.status })
      }
      if (err instanceof ValidationRejectedError) {
        // The server revalidated (it always does) and said no -- show
        // ITS fresh view of the reports, not our stale one.
        setValidation({
          status: 'done',
          result: err.validation as IngestionValidationDTO,
          note: err.code === 'STALE_VALIDATION'
            ? 'The selected files changed after they were validated — review the fresh results below and acknowledge again.'
            : 'The server re-checked the reports and found conditions that need review below.',
        })
        setAck(false)
        setRunState({ status: 'idle' })
      } else {
        setRunState({ status: 'error', message: err instanceof Error ? err.message : 'Unexpected error' })
      }
    }
  }

  return (
    <div className="h-full flex flex-col bg-slate-50 overflow-hidden">
      {/* Page Header */}
      <div className="bg-white border-b border-slate-100 px-4 sm:px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-[22px] font-bold text-slate-900 leading-tight">Inventory Sync</h1>
            <p className="text-[13px] text-slate-500 mt-0.5">
              Upload dealership reports to reconcile Tekion, Keyper, MDD, RecovR, and RapidRecon
            </p>
          </div>
          <div className="flex items-center gap-3">
            {history.length > 0 && (
              <div className="text-[12px] text-slate-500">
                Last sync {formatTimestamp(history[0].started_at)}
              </div>
            )}
            <button
              onClick={handleRunSync}
              disabled={!canRun || runState.status === 'running'}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-200 disabled:text-slate-400 text-white text-[13px] font-medium px-4 py-2 rounded-xl transition-colors"
            >
              {runState.status === 'running' ? spinner : <RefreshIcon />}
              {runState.status === 'running' ? 'Running Sync…' : 'Run Sync Now'}
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-4 sm:px-6 py-5 flex flex-col gap-5">
        {/* Upload Reports -- 1 col on phones, 2 on tablet-portrait/narrow
            windows, 3 (unchanged) from lg up */}
        <div className="bg-white rounded-2xl border border-slate-100 p-4">
          <h2 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3">
            Upload Reports
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {UPLOAD_SLOTS.map(slot => {
              const file = files[slot.field]
              return (
                <label
                  key={slot.field}
                  className={`relative flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-[13px] cursor-pointer transition-all focus-within:ring-2 focus-within:ring-blue-300 ${
                    file
                      ? 'border-blue-200 bg-blue-50 text-blue-700'
                      : 'border-slate-100 bg-white text-slate-600 hover:border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <UploadIcon className={file ? 'text-blue-500' : 'text-slate-400'} />
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold truncate">{slot.label}</div>
                    <div className="text-[11px] text-slate-500 truncate">{file ? file.name : 'No file selected'}</div>
                  </div>
                  {/* Sprint 14 (Rail K): display:none removed a
                      keyboard user's only path to selecting a file --
                      visually hidden but focusable instead; the label
                      draws the focus ring via focus-within. */}
                  <input
                    type="file"
                    accept=".csv"
                    className="visually-hidden"
                    onChange={e => handleFileChange(slot.field, e.target.files?.[0])}
                  />
                </label>
              )
            })}
          </div>

          {/* Sprint 10: validation is the step between selecting files
              and being allowed to run. */}
          <div className="mt-3 flex items-center gap-3 flex-wrap">
            <button
              onClick={handleValidate}
              disabled={selectedCount === 0 || validation.status === 'validating'}
              className="flex items-center gap-2 bg-slate-800 hover:bg-slate-900 disabled:bg-slate-100 disabled:text-slate-400 text-white text-[13px] font-medium px-4 py-2 rounded-xl transition-colors"
            >
              {validation.status === 'validating' ? spinner : <SearchIcon />}
              {validation.status === 'validating' ? 'Validating…' : 'Validate Reports'}
            </button>
            <span role="status" className="text-[12px] text-slate-500">
              {validation.status === 'done'
                ? `Validated ${formatTimestamp(validation.result.validated_at)} — nothing has been changed yet.`
                : 'Reports are validated and previewed before anything is synced.'}
            </span>
          </div>

          {validation.status === 'error' && (
            <div role="alert" className="mt-3 flex items-start gap-2 bg-red-50 border border-red-100 rounded-xl px-3 py-2.5 text-[12px] text-red-700">
              <WarningIcon className="text-red-500 mt-0.5 shrink-0" />
              <span>{validation.message}</span>
            </div>
          )}
          {runState.status === 'error' && (
            <div role="alert" className="mt-3 flex items-start gap-2 bg-red-50 border border-red-100 rounded-xl px-3 py-2.5 text-[12px] text-red-700">
              <WarningIcon className="text-red-500 mt-0.5 shrink-0" />
              <span>{runState.message}</span>
            </div>
          )}
          {runState.status === 'success' && (
            <div role="status" className="mt-3 flex items-center gap-2 bg-emerald-50 border border-emerald-100 rounded-xl px-3 py-2.5 text-[12px] text-emerald-700">
              <span>
                Sync complete — {summary?.vehicles_processed.toLocaleString()} vehicles processed across{' '}
                {summary?.sync_runs.length} source{summary?.sync_runs.length === 1 ? '' : 's'}.
              </span>
            </div>
          )}
        </div>

        {/* Pre-Sync Preview (Sprint 10) */}
        {validation.status === 'done' && (
          <div className="bg-white rounded-2xl border border-slate-100 p-4">
            <h2 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3">
              Pre-Sync Preview
            </h2>

            {validation.note && (
              <div role="alert" className="mb-3 flex items-start gap-2 bg-amber-50 border border-amber-100 rounded-xl px-3 py-2.5 text-[12px] text-amber-800">
                <WarningIcon className="text-amber-500 mt-0.5 shrink-0" />
                <span>{validation.note}</span>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              {validation.result.reports.map(report => (
                <ReportPreviewCard key={report.slot} report={report} />
              ))}
            </div>

            {validation.result.status === 'rejected' && (
              <div className="mt-3 flex items-start gap-2 bg-red-50 border border-red-100 rounded-xl px-3 py-2.5 text-[12px] text-red-700">
                <CrossIcon className="text-red-500 mt-0.5 shrink-0" />
                <span>
                  Rejected reports never reach the sync engine. Fix the export (or choose the right
                  file), reselect it, and validate again.
                </span>
              </div>
            )}

            {validation.result.requires_acknowledgement && validation.result.status !== 'rejected' && (
              <label className="mt-3 flex items-start gap-2.5 bg-amber-50 border border-amber-100 rounded-xl px-3 py-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={ack}
                  onChange={e => setAck(e.target.checked)}
                  className="mt-0.5 accent-amber-600"
                />
                <span className="text-[12px] text-amber-900 leading-snug">
                  I reviewed the warnings above and confirm these reports reflect reality — run the
                  sync with them.
                </span>
              </label>
            )}
          </div>
        )}

        {/* Recent Sync Runs */}
        <div className="bg-white rounded-2xl border border-slate-100 p-4">
          <h2 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3">
            Recent Sync Runs
          </h2>
          {history.length === 0 ? (
            <p className="text-[13px] text-slate-500">No syncs recorded yet — upload reports above to get started.</p>
          ) : (
            <div className="flex items-center gap-2 flex-wrap">
              {history.slice(0, 6).map(batch => (
                <div
                  key={batch.started_at}
                  className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl border border-slate-100 bg-white text-[13px]"
                >
                  <SystemDot status={batch.overall_status} />
                  <span className="visually-hidden">{statusLabel(batch.overall_status)}.</span>
                  <span className="font-semibold text-slate-700">{formatTimestamp(batch.started_at)}</span>
                  <span className="text-[11px] text-slate-500">
                    {batch.sources.map(s => sourceLabel(s.source)).join(', ')}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
          {[
            { label: 'Vehicles Processed', value: summary?.vehicles_processed ?? '—', color: 'text-blue-600' },
            { label: 'Exceptions', value: summary?.exceptions_found ?? exceptions.length, color: 'text-amber-600' },
            { label: 'Tasks Generated', value: summary?.tasks_generated ?? '—', color: 'text-slate-700' },
            { label: 'Recommendations', value: summary?.recommendations_generated ?? '—', color: 'text-violet-600' },
          ].map(stat => (
            <div key={stat.label} className="bg-white rounded-2xl border border-slate-100 px-5 py-4">
              <p className="text-[12px] text-slate-500 mb-1">{stat.label}</p>
              <p className={`text-[28px] font-bold leading-none ${stat.color}`}>{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Two-column body -- stacks below lg */}
        <div className="flex flex-col lg:flex-row gap-5 items-start pb-8">
          {/* Left: exceptions table (60%) */}
          <div className="w-full lg:flex-[3] min-w-0">
            <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 flex-wrap gap-2">
                <div className="flex items-center gap-2.5">
                  <h2 className="text-[15px] font-semibold text-slate-900">Exceptions</h2>
                  <span className="bg-amber-100 text-amber-700 text-[11px] font-semibold px-2 py-0.5 rounded-full">
                    {exceptions.length}
                  </span>
                </div>
                <div className="relative w-full sm:w-auto">
                  <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    aria-label="Search exceptions"
                    placeholder="Search exceptions…"
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="pl-8 pr-3 py-1.5 text-[12px] border border-slate-200 rounded-lg bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 w-full sm:w-52 text-slate-700 placeholder-slate-400"
                  />
                </div>
              </div>

              <div className="overflow-y-auto" style={{ maxHeight: '440px' }}>
                {exceptionsState.status === 'error' ? (
                  <div className="text-center py-10 text-slate-500 text-[13px]">
                    {isBackendUnavailable(exceptionsState.error)
                      ? 'The LotSync API is unreachable.'
                      : 'Could not load exceptions.'}
                  </div>
                ) : filteredExceptions.length === 0 ? (
                  <div className="text-center py-10 text-slate-500 text-[13px]">
                    {exceptionsState.status === 'loading' ? 'Loading…' : 'No exceptions match your search.'}
                  </div>
                ) : (
                  <>
                    {/* Below lg: stacked cards -- the table's five
                        whitespace-nowrap columns can't fit a phone/tablet
                        width without clipping or a horizontal scrollbar,
                        so this mirrors VehiclesList.tsx's table->card
                        pattern instead of introducing horizontal scroll. */}
                    <div className="lg:hidden divide-y divide-slate-50">
                      {filteredExceptions.map(e => (
                        <div key={e.pending_identity_id} className="px-4 py-3 border-l-2 border-l-amber-400">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono text-[12px] text-slate-800 font-medium">{e.raw_identifier}</span>
                            <span className="bg-slate-100 text-slate-600 text-[11px] font-medium px-2 py-0.5 rounded-md">{sourceLabel(e.source)}</span>
                          </div>
                          <div className="text-[12px] text-slate-700 leading-snug mt-1" title={e.identifier_type}>{exceptionReason(e.identifier_type)}</div>
                          <div className="text-[11px] text-slate-500 mt-1.5">
                            First {formatTimestamp(e.first_observed_at)} · Last {formatTimestamp(e.last_observed_at)}
                          </div>
                        </div>
                      ))}
                    </div>

                    <table className="hidden lg:table w-full text-[12px]">
                      <thead className="sticky top-0 bg-slate-50 z-10">
                        <tr className="border-b border-slate-100">
                          <th scope="col" className="text-left px-4 py-2.5 font-semibold text-slate-500 text-[11px] uppercase tracking-wider whitespace-nowrap">Identifier</th>
                          <th scope="col" className="text-left px-4 py-2.5 font-semibold text-slate-500 text-[11px] uppercase tracking-wider">Reason</th>
                          <th scope="col" className="text-left px-4 py-2.5 font-semibold text-slate-500 text-[11px] uppercase tracking-wider whitespace-nowrap">Source</th>
                          <th scope="col" className="text-left px-4 py-2.5 font-semibold text-slate-500 text-[11px] uppercase tracking-wider whitespace-nowrap">First Observed</th>
                          <th scope="col" className="text-left px-4 py-2.5 font-semibold text-slate-500 text-[11px] uppercase tracking-wider whitespace-nowrap">Last Observed</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredExceptions.map((e, idx) => (
                          <tr
                            key={e.pending_identity_id}
                            className={`border-b border-slate-50 last:border-0 ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'} border-l-2 border-l-amber-400`}
                          >
                            <td className="px-4 py-3 align-top whitespace-nowrap">
                              <span className="font-mono text-[12px] text-slate-800 font-medium">{e.raw_identifier}</span>
                            </td>
                            <td className="px-4 py-3 align-top text-slate-700 leading-snug" title={e.identifier_type}>{exceptionReason(e.identifier_type)}</td>
                            <td className="px-4 py-3 align-top whitespace-nowrap">
                              <span className="bg-slate-100 text-slate-600 text-[11px] font-medium px-2 py-0.5 rounded-md">{sourceLabel(e.source)}</span>
                            </td>
                            <td className="px-4 py-3 align-top text-slate-500 whitespace-nowrap">{formatTimestamp(e.first_observed_at)}</td>
                            <td className="px-4 py-3 align-top text-slate-500 whitespace-nowrap">{formatTimestamp(e.last_observed_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Right column (40%) */}
          <div className="w-full lg:flex-[2] min-w-0 flex flex-col gap-4">
            {/* System Status */}
            <div className="bg-white rounded-2xl border border-slate-100">
              <div className="px-5 py-4 border-b border-slate-100">
                <h2 className="text-[15px] font-semibold text-slate-900">System Status</h2>
              </div>
              <div className="divide-y divide-slate-50">
                {Object.keys(connectedSystems).length === 0 ? (
                  <div className="px-5 py-4 text-[13px] text-slate-500">No syncs recorded yet.</div>
                ) : (
                  Object.entries(connectedSystems).map(([source, status]) => (
                    <div key={source} className="px-5 py-3 flex items-start gap-3">
                      <div className="mt-1.5"><SystemDot status={status.status} /></div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[13px] font-semibold text-slate-800">{sourceLabel(source)}</span>
                          <span className={`text-[11px] font-medium ${status.status === 'complete' ? 'text-emerald-600' : status.status === 'failed' ? 'text-red-600' : 'text-amber-600'}`}>
                            {statusLabel(status.status)}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">
                          {status.records_processed?.toLocaleString() ?? '0'} records · {formatTimestamp(status.started_at)}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Detected Changes */}
            <div className="bg-white rounded-2xl border border-slate-100">
              <div className="px-5 py-4 border-b border-slate-100">
                <h2 className="text-[15px] font-semibold text-slate-900">Detected Changes</h2>
              </div>
              <div className="px-5 py-4 flex flex-col gap-3">
                {summary ? (
                  <>
                    <div className="flex items-center gap-3">
                      <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-blue-50 text-blue-600 shrink-0"><TaskIcon /></span>
                      <span className="text-[13px] font-semibold text-slate-800">{summary.tasks_generated} new tasks generated</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-violet-50 text-violet-500 shrink-0"><LightbulbIcon /></span>
                      <span className="text-[13px] text-slate-700">{summary.recommendations_generated} recommendations surfaced</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-amber-50 text-amber-600 shrink-0"><WarningIcon /></span>
                      <span className="text-[13px] text-slate-700">{summary.exceptions_found} exceptions detected this run</span>
                    </div>
                  </>
                ) : (
                  <p className="text-[13px] text-slate-500">Run a sync to see what changed.</p>
                )}
              </div>
            </div>

            {/* Run History */}
            <div className="bg-white rounded-2xl border border-slate-100">
              <div className="px-5 py-4 border-b border-slate-100">
                <h2 className="text-[15px] font-semibold text-slate-900">Run History</h2>
              </div>
              <div className="divide-y divide-slate-50">
                {historyState.status === 'loading' && (
                  <div className="px-5 py-4 text-[13px] text-slate-500">Loading…</div>
                )}
                {historyState.status === 'error' && (
                  <div className="px-5 py-4 text-[13px] text-slate-500">
                    {isBackendUnavailable(historyState.error) ? 'The LotSync API is unreachable.' : 'Could not load history.'}
                  </div>
                )}
                {historyState.status === 'success' && history.length === 0 && (
                  <div className="px-5 py-4 text-[13px] text-slate-500">No syncs recorded yet.</div>
                )}
                {history.map(batch => (
                  <div key={batch.started_at} className="px-5 py-2.5 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <SystemDot status={batch.overall_status} />
                      <span className="visually-hidden">{statusLabel(batch.overall_status)}.</span>
                      <span className="text-[12px] text-slate-700">{formatTimestamp(batch.started_at)}</span>
                    </div>
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
                      {batch.sources.length} source{batch.sources.length === 1 ? '' : 's'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
