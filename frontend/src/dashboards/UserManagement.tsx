/**
 * Sprint 09 -- the Manager/Admin user-administration surface (Rail A).
 *
 * Renders only for roles the server itself considers user-admins; the
 * role split shown here (which roles the invite dropdown offers,
 * which rows offer deactivate/reactivate) mirrors the SERVER policy
 * in api/routers/users.py -- the server enforces it regardless of
 * anything this UI does:
 *
 *   admin    -> may grant/administer all four roles
 *   manager  -> lot_staff and sales_manager only
 *
 * The dealership is never chosen here: the API derives it from the
 * caller's own membership.
 */

import { useCallback, useEffect, useState } from 'react'
import { ApiError, apiGet, apiPostJson } from '../api/client'
import { ROLE_LABELS, useMe } from '../auth/AccessProvider'
import { track } from '../observability/analytics'

interface RosterEntry {
  auth_user_id: string
  email: string | null
  display_name: string | null
  role: string
  active: boolean
  account_state: 'active' | 'invited' | 'unknown'
}

const GRANTABLE: Record<string, string[]> = {
  admin: ['admin', 'manager', 'lot_staff', 'sales_manager'],
  manager: ['lot_staff', 'sales_manager'],
}

export default function UserManagement() {
  const me = useMe()
  const [roster, setRoster] = useState<RosterEntry[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('lot_staff')
  const [inviteBusy, setInviteBusy] = useState(false)
  const [inviteNotice, setInviteNotice] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)
  const [rowBusy, setRowBusy] = useState<string | null>(null)
  const [rowError, setRowError] = useState<string | null>(null)

  const myRole = me?.role ?? ''
  const grantable = GRANTABLE[myRole] ?? []

  const load = useCallback(() => {
    setLoadError(null)
    apiGet<RosterEntry[]>('/users')
      .then(setRoster)
      .catch((error: unknown) => {
        setLoadError(error instanceof ApiError ? error.message : 'Could not load users.')
      })
  }, [])

  useEffect(() => { load() }, [load])

  // Sprint 11 (analytics): a Manager/Admin opened the roster -- once
  // per mount, no user data attached.
  useEffect(() => { track('user_management_opened') }, [])

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault()
    if (inviteBusy) return
    setInviteBusy(true)
    setInviteNotice(null)
    try {
      const created = await apiPostJson<RosterEntry>('/users/invite', {
        email: inviteEmail.trim(),
        role: inviteRole,
      })
      setInviteNotice({
        kind: 'ok',
        text: created.account_state === 'invited'
          ? `Invitation sent to ${created.email}.`
          : `${created.email} added to the dealership.`,
      })
      setInviteEmail('')
      load()
    } catch (error: unknown) {
      setInviteNotice({
        kind: 'error',
        text: error instanceof ApiError ? error.message : 'Invite failed.',
      })
    } finally {
      setInviteBusy(false)
    }
  }

  async function setActive(entry: RosterEntry, active: boolean) {
    if (rowBusy) return
    setRowBusy(entry.auth_user_id)
    setRowError(null)
    try {
      await apiPostJson<RosterEntry>(
        `/users/${encodeURIComponent(entry.auth_user_id)}/${active ? 'reactivate' : 'deactivate'}`,
        {},
      )
      load()
    } catch (error: unknown) {
      setRowError(error instanceof ApiError ? error.message : 'Update failed.')
    } finally {
      setRowBusy(null)
    }
  }

  const canAdminister = (entry: RosterEntry) =>
    grantable.includes(entry.role) && entry.auth_user_id !== undefined

  return (
    <div className="flex flex-col gap-5">
      {/* Invite */}
      <div className="bg-white rounded-xl border border-slate-100 p-5">
        <p className="text-[13px] font-semibold text-slate-700 mb-1">Invite a user</p>
        <p className="text-[11px] text-slate-400 mb-4">
          They&rsquo;ll receive an email link to set their password. Accounts are
          created for this dealership only.
        </p>
        <form onSubmit={handleInvite} className="flex flex-col sm:flex-row gap-3">
          <input
            type="email" required value={inviteEmail}
            onChange={e => setInviteEmail(e.target.value)}
            placeholder="person@dealership.com"
            className="flex-1 px-3 py-2 text-[13px] border border-slate-200 rounded-lg bg-white text-slate-800 placeholder:text-slate-300 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all"
          />
          <select
            value={inviteRole}
            onChange={e => setInviteRole(e.target.value)}
            className="px-3 py-2 text-[13px] border border-slate-200 rounded-lg bg-white text-slate-700 focus:outline-none focus:border-blue-400"
          >
            {grantable.map(role => (
              <option key={role} value={role}>{ROLE_LABELS[role] ?? role}</option>
            ))}
          </select>
          <button
            type="submit" disabled={inviteBusy}
            className="px-5 py-2 bg-blue-600 text-white text-[13px] font-semibold rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-60">
            {inviteBusy ? 'Inviting…' : 'Invite'}
          </button>
        </form>
        {inviteNotice && (
          <div role="alert"
            className={`mt-3 text-[12px] rounded-lg px-3 py-2 border ${
              inviteNotice.kind === 'ok'
                ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                : 'text-red-700 bg-red-50 border-red-200'
            }`}>
            {inviteNotice.text}
          </div>
        )}
      </div>

      {/* Roster */}
      <div className="bg-white rounded-xl border border-slate-100 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <p className="text-[13px] font-semibold text-slate-700">Dealership users</p>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Deactivating removes access immediately; the account and its
            history are kept and can be reactivated.
          </p>
        </div>
        {roster === null && !loadError && (
          <div className="px-5 py-6 text-[12px] text-slate-400">Loading users…</div>
        )}
        {loadError && (
          <div className="px-5 py-6 text-[12px] text-red-600" role="alert">{loadError}</div>
        )}
        {rowError && (
          <div className="mx-5 mt-3 text-[12px] rounded-lg px-3 py-2 border text-red-700 bg-red-50 border-red-200" role="alert">
            {rowError}
          </div>
        )}
        {roster !== null && (
          <div className="divide-y divide-slate-50">
            {roster.length === 0 && (
              <div className="px-5 py-6 text-[12px] text-slate-400">
                No users yet. Invite the first one above.
              </div>
            )}
            {roster.map(entry => {
              // Self rows render like any other; the server refuses
              // self-administration, and that refusal message is shown.
              const name = entry.display_name || entry.email || entry.auth_user_id
              return (
                <div key={entry.auth_user_id}
                     className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 px-5 py-3.5">
                  <div className="flex-1 min-w-0">
                    <p className={`text-[13px] font-medium truncate ${entry.active ? 'text-slate-700' : 'text-slate-400 line-through'}`}>
                      {name}
                    </p>
                    <p className="text-[11px] text-slate-400 truncate">
                      {entry.display_name ? entry.email : null}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                      {ROLE_LABELS[entry.role] ?? entry.role}
                    </span>
                    {entry.account_state === 'invited' && (
                      <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                        Invited
                      </span>
                    )}
                    {!entry.active && (
                      <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-red-50 text-red-600 border border-red-200">
                        Deactivated
                      </span>
                    )}
                    {canAdminister(entry) && (
                      entry.active ? (
                        <button
                          onClick={() => { void setActive(entry, false) }}
                          disabled={rowBusy === entry.auth_user_id}
                          className="px-3 py-1.5 text-[12px] font-medium border border-red-200 rounded-lg text-red-600 hover:bg-red-50 transition-colors disabled:opacity-60">
                          Deactivate
                        </button>
                      ) : (
                        <button
                          onClick={() => { void setActive(entry, true) }}
                          disabled={rowBusy === entry.auth_user_id}
                          className="px-3 py-1.5 text-[12px] font-medium border border-emerald-200 rounded-lg text-emerald-700 hover:bg-emerald-50 transition-colors disabled:opacity-60">
                          Reactivate
                        </button>
                      )
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
