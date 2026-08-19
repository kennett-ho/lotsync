/**
 * Sprint 12 (Rail B) -- Help & Getting Started.
 *
 * A lightweight reference surface, not a docs site: short sections in
 * operational language covering only what actually exists. Sections
 * are role-aware where the underlying surface is (Inventory Sync
 * guidance renders only for roles that can run a sync; User
 * Management guidance only for user admins) -- presentation-layer
 * mirrors of the server sets in roleNav.ts, never authorization.
 * "Replay the tour" re-opens the Getting Started sequence (App.tsx
 * owns that state and the analytics events).
 */

import { useEffect } from 'react'
import { useMe } from '../auth/AccessProvider'
import { track } from '../observability/analytics'
import { SYNC_CONTROL_ROLES, USER_ADMIN_ROLES } from '../roleNav'

interface HelpSection { id: string; title: string; body: string[] }

const SHARED_SECTIONS: HelpSection[] = [
  {
    id: 'what-is',
    title: 'What is DealerDOH?',
    body: [
      'DealerDOH connects evidence from your dealership systems — Tekion, Keyper, MDD, RecovR, RapidRecon — and surfaces the operational work that evidence supports. It does not replace those systems, and it does not make decisions: your team does.',
      'If a number looks wrong, the first question is always "what did the source systems last report, and when?" — every vehicle page shows exactly that.',
    ],
  },
  {
    id: 'tasks',
    title: 'Understanding Tasks',
    body: [
      'A task is committed, actionable work on one specific vehicle — for example installing a RecovR device or investigating a key that has been checked out too long.',
      'Tasks have two independent facts: whether the commitment still stands (outstanding, completed, no longer needed, cancelled, superseded) and how execution is going (not started, in progress, blocked, completed). DealerDOH keeps both visible rather than collapsing them.',
      '"Standing Policy" tasks were generated automatically by dealership rules; "Ratified by Person" tasks were confirmed by a human.',
    ],
  },
  {
    id: 'recommendations',
    title: 'Understanding Recommendations',
    body: [
      'A recommendation is evidence surfaced for human review — a pattern worth someone’s judgment, like a key checked out so long the vehicle is likely sold.',
      'Recommendations are not committed work and nothing happens automatically. A person reviews the evidence and decides.',
    ],
  },
  {
    id: 'vehicles',
    title: 'Vehicles & the evidence timeline',
    body: [
      'Every vehicle page shows its identity, what each connected system currently reports, and a timeline of observed events with their timestamps.',
      'The timeline is the "why" behind tasks and recommendations: when a task says a key has been out too long, the Keyper events on the vehicle are the evidence.',
      'The Vehicles list shows active inventory by default; the Sold filter shows vehicles Tekion reports as sold — useful when a sold vehicle still has a key in the cabinet or a device to recover.',
    ],
  },
]

const SYNC_SECTION: HelpSection = {
  id: 'inventory-sync',
  title: 'Inventory Sync',
  body: [
    'Inventory Sync is where dealership reports enter DealerDOH. Every uploaded report is validated first: DealerDOH identifies what kind of report it actually is from its content, checks it against that report’s rules, and previews what it found before anything changes.',
    'An error means the evidence cannot be trusted and nothing is processed. A warning means the evidence may be valid but needs your review — for example a vehicle count that dropped sharply. Warnings must be explicitly acknowledged before a sync runs; nothing is acknowledged for you.',
    'Timestamps on the Overview and each vehicle show when evidence last arrived from each system. Stale evidence is not current evidence.',
  ],
}

const USER_ADMIN_SECTION: HelpSection = {
  id: 'account-access',
  title: 'Account & access',
  body: [
    'Everyone signs in with their dealership email. Roles (Manager, Lot Staff, Sales Manager, Admin) are assigned by your dealership’s administrators and decide what each person can do — assignments live in User Management, under Profile & Settings.',
    'Public self-signup is disabled: accounts exist only by invitation.',
  ],
}

const ACCOUNT_SECTION: HelpSection = {
  id: 'account-access',
  title: 'Account & access',
  body: [
    'You sign in with your dealership email. Your role and dealership are assigned by your dealership’s administrators — if access looks wrong, contact a manager or administrator.',
    'Password resets are emailed from Profile & Settings.',
  ],
}

const TROUBLESHOOTING_SECTION: HelpSection = {
  id: 'troubleshooting',
  title: 'Troubleshooting',
  body: [
    'If something fails unexpectedly, the error panel shows a short reference code — sharing that code with support lets them find exactly what happened.',
    'If data looks stale, check the sync timestamp in the header. If a page won’t load, try reloading; your sign-in survives a reload.',
  ],
}

export default function Help({ onReplayOnboarding }: { onReplayOnboarding: () => void }) {
  const me = useMe()
  const role = me?.role

  // Sprint 12 analytics: where do users seek additional explanation?
  useEffect(() => { track('help_opened') }, [])

  const sections: HelpSection[] = [
    ...SHARED_SECTIONS,
    ...(role && SYNC_CONTROL_ROLES.includes(role) ? [SYNC_SECTION] : []),
    role && USER_ADMIN_ROLES.includes(role) ? USER_ADMIN_SECTION : ACCOUNT_SECTION,
    TROUBLESHOOTING_SECTION,
  ]

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-5">
          <div>
            <h1 className="text-[20px] font-bold text-slate-900 leading-tight">Help &amp; Getting Started</h1>
            <p className="text-[13px] text-slate-500 mt-0.5">Short explanations of what you’re seeing and why.</p>
          </div>
          <button onClick={onReplayOnboarding}
            className="text-[12px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 hover:bg-blue-100 px-3.5 py-2 rounded-lg transition-colors">
            Replay the Getting Started tour
          </button>
        </div>

        <div className="space-y-3">
          {sections.map(section => (
            <section key={section.id} className="bg-white rounded-2xl border border-slate-100 px-5 py-4">
              <h2 className="text-[14px] font-bold text-slate-900 mb-2">{section.title}</h2>
              <div className="space-y-2">
                {section.body.map((p, i) => (
                  <p key={i} className="text-[13px] text-slate-600 leading-relaxed">{p}</p>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  )
}
