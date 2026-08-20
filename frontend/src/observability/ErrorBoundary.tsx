/**
 * Sprint 11 (phase 13) -- the honest fallback for unexpected React
 * render failures. Before this sprint a render error meant a blank
 * screen; now the user is told plainly that DealerDOH hit an
 * unexpected problem, offered a reload, and (when Sentry is enabled)
 * given a safe reference id -- no stack traces, no internals, no
 * pretending anything saved.
 *
 * Mounted OUTSIDE the auth gate in main.tsx so gate/login render
 * failures are caught too. The DEV banner is re-rendered inside the
 * fallback (the crashed tree took the normal one down with it).
 */

import React from 'react'
import { OBS_ENVIRONMENT } from './config'
import { captureUnexpected } from './sentry'

type State = { error: unknown | null; eventId: string }

export default class ErrorBoundary extends React.Component<
  { children: React.ReactNode }, State
> {
  state: State = { error: null, eventId: '' }

  static getDerivedStateFromError(error: unknown): Partial<State> {
    return { error }
  }

  componentDidCatch(error: unknown): void {
    this.setState({ eventId: captureUnexpected(error) })
  }

  render() {
    if (this.state.error === null) return this.props.children

    return (
      <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#F8FAFC' }}>
        {OBS_ENVIRONMENT === 'development' && (
          <div className="bg-amber-400 text-amber-950 text-[12px] font-semibold text-center py-1">
            DealerDOH DEV — Development Environment — Synthetic/Test Data Only
          </div>
        )}
        <div className="flex-1 flex items-center justify-center px-4">
          <div role="alert" className="w-full max-w-md bg-white border border-slate-200 rounded-2xl p-6 text-center shadow-sm">
            <div className="text-[15px] font-semibold text-slate-900 mb-2">
              DealerDOH hit an unexpected problem
            </div>
            <p className="text-[13px] text-slate-500 mb-5 leading-relaxed">
              The page couldn&rsquo;t continue. Nothing you submitted is assumed
              saved — reload and check before repeating any action. If this
              keeps happening, tell your manager or administrator.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white text-[13px] font-semibold py-2.5 rounded-xl transition-colors"
            >
              Reload DealerDOH
            </button>
            {this.state.eventId && (
              <p className="mt-4 text-[11px] text-slate-500 font-mono">
                Reference: {this.state.eventId}
              </p>
            )}
          </div>
        </div>
      </div>
    )
  }
}
