/**
 * Sprint 12 (Rail B) -- the role-aware Getting Started tour.
 *
 * A short modal sequence (3-4 steps), not a tutorial platform: what
 * DealerDOH is, what the user's landing surface shows, why work
 * exists, where Help lives. Steps are chosen by the SERVER-confirmed
 * role; content never mentions surfaces the role cannot use, and
 * finishing/skipping never grants anything -- authorization is
 * untouched. Copy is operational on purpose (Phase 22): dealership
 * work, not marketing.
 *
 * Skip and finish both record completion (ROLE_AWARE_UX.md S12-10);
 * replay lives in Help. Analytics: the deliberate lifecycle events
 * only -- fired by App.tsx at the decision points, not in here, so
 * one seam owns the taxonomy.
 */

import { useEffect, useRef, useState } from 'react'

interface Step { title: string; body: string[] }

const WHAT_IS_DEALERDOH: Step = {
  title: 'Welcome to DealerDOH',
  body: [
    'DealerDOH brings evidence from your dealership systems — Tekion, Keyper, MDD, RecovR, RapidRecon — into one place, so you can see what needs attention.',
    'Systems provide evidence. DealerDOH connects it. Your team makes the decisions.',
  ],
}

const HELP_STEP: Step = {
  title: 'When something is unclear',
  body: [
    'Help (in the sidebar) explains tasks, recommendations, vehicles, and syncing — and you can replay this tour from there any time.',
  ],
}

const MANAGER_STEPS: Step[] = [
  WHAT_IS_DEALERDOH,
  {
    title: 'Overview answers "what needs attention?"',
    body: [
      'Your landing page shows open work grouped by type, recommendations awaiting judgment, inventory health, and whether the latest sync succeeded.',
      'Recommendations are evidence surfaced for a human decision — nothing is committed until someone acts on it.',
    ],
  },
  {
    title: 'Evidence comes in through Inventory Sync',
    body: [
      'Upload dealership reports there. DealerDOH validates every report and previews what it found before anything changes — suspicious evidence is held for your review, never processed silently.',
      'Timestamps throughout the app show when evidence last arrived. Stale evidence is not current evidence.',
    ],
  },
  HELP_STEP,
]

const LOT_STAFF_STEPS: Step[] = [
  WHAT_IS_DEALERDOH,
  {
    title: "Today's Work is your starting point",
    body: [
      'It lists the outstanding work on the lot right now, grouped by what kind of job it is, with the vehicle and the reason side by side.',
      'Need it on paper? Generate Work Order gives you the printable list.',
    ],
  },
  {
    title: 'Every task says why',
    body: [
      'Each task exists because connected systems reported something — a key checked out too long, a device not installed. Open the vehicle to see the evidence behind it, including when each system last reported.',
    ],
  },
  HELP_STEP,
]

const SHARED_STEPS: Step[] = [
  WHAT_IS_DEALERDOH,
  {
    title: 'Overview, Vehicles, and Tasks',
    body: [
      'Overview shows what needs attention across the operation. Vehicles is the inventory — open any vehicle to see its full evidence timeline. Tasks is the operational work queue.',
    ],
  },
  HELP_STEP,
]

export function stepsForRole(role: string | undefined): Step[] {
  if (role === 'admin' || role === 'manager') return MANAGER_STEPS
  if (role === 'lot_staff') return LOT_STAFF_STEPS
  return SHARED_STEPS
}

export default function Onboarding({ role, onFinish, onSkip }: {
  role: string | undefined
  onFinish: () => void
  onSkip: () => void
}) {
  const steps = stepsForRole(role)
  const [index, setIndex] = useState(0)
  // Clamp BOTH the read and the advance: rapid double-clicks queue
  // multiple functional setIndex updates against one render's stale
  // `last`, which can push index past the final step -- steps[index]
  // then renders undefined and crashes the boundary (found live in
  // the Sprint 12 deployed smoke; Sentry ref 9f338b8d).
  const step = steps[Math.max(0, Math.min(index, steps.length - 1))]
  const last = index >= steps.length - 1
  const clampedIndex = Math.max(0, Math.min(index, steps.length - 1))

  // Sprint 14 (Rail K): real modal behavior to match the dialog
  // semantics the markup already claimed. Focus moves INTO the dialog
  // on open (the panel itself, so the title reads first), Tab cycles
  // inside it (aria-modal told AT the background is inert; the trap
  // makes that true for the keyboard too), and Escape dismisses via
  // onSkip -- the same never-nag semantics as the Skip button
  // (ROLE_AWARE_UX.md S12-10: skip records completion). App.tsx
  // returns focus afterward through its surface-focus seam.
  const panelRef = useRef<HTMLDivElement>(null)
  useEffect(() => { panelRef.current?.focus() }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.stopPropagation()
      onSkip()
      return
    }
    if (e.key !== 'Tab') return
    const panel = panelRef.current
    if (!panel) return
    const focusables = Array.from(
      panel.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'),
    )
    if (focusables.length === 0) return
    const first = focusables[0]
    const lastEl = focusables[focusables.length - 1]
    const active = document.activeElement
    if (e.shiftKey && (active === first || active === panel)) {
      e.preventDefault()
      lastEl.focus()
    } else if (!e.shiftKey && active === lastEl) {
      e.preventDefault()
      first.focus()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ backgroundColor: 'rgba(11, 18, 32, 0.62)' }}
      role="dialog" aria-modal="true" aria-label="Getting started"
      onKeyDown={handleKeyDown}>
      <div ref={panelRef} tabIndex={-1}
        className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden outline-none">
        <div className="px-6 pt-6 pb-5">
          {/* Sprint 14 (Rail K): the current position is announced on
              every step change (the dots below are visual-only). */}
          <p role="status" className="visually-hidden">
            Step {clampedIndex + 1} of {steps.length}: {step.title}
          </p>
          <div className="flex items-start justify-between gap-3">
            <h2 className="text-[17px] font-bold text-slate-900 leading-snug">{step.title}</h2>
            <button onClick={onSkip} aria-label="Skip the tour"
              className="flex-shrink-0 w-7 h-7 -mt-1 -mr-1 flex items-center justify-center rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors">
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
            </button>
          </div>
          <div className="mt-3 space-y-2.5">
            {step.body.map((p, i) => (
              <p key={i} className="text-[13px] text-slate-600 leading-relaxed">{p}</p>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between px-6 py-4 bg-slate-50 border-t border-slate-100">
          <div className="flex items-center gap-1.5" aria-hidden="true">
            {steps.map((_, i) => (
              <span key={i} className={`w-1.5 h-1.5 rounded-full ${i === clampedIndex ? 'bg-blue-600' : 'bg-slate-300'}`} />
            ))}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onSkip}
              className="text-[12px] font-medium text-slate-500 hover:text-slate-700 px-3 py-2 transition-colors">
              Skip for now
            </button>
            {index > 0 && (
              <button onClick={() => setIndex(i => Math.max(i - 1, 0))}
                className="text-[12px] font-semibold text-slate-600 bg-white border border-slate-200 hover:border-slate-300 px-4 py-2 rounded-lg transition-colors">
                Back
              </button>
            )}
            <button
              onClick={() => (last ? onFinish() : setIndex(i => Math.min(i + 1, steps.length - 1)))}
              className="text-[12px] font-bold text-white bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg transition-colors">
              {last ? 'Get started' : 'Next'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
