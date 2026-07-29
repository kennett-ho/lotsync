const roleMeta: Record<string, { description: string; features: string[] }> = {
  'Sales Manager': {
    description: 'Sales pipeline, customer deliveries, and floor activity at a glance.',
    features: ['Active deals in progress', 'Customer delivery schedule', 'Trade-in queue', 'Sales team leaderboard', 'Floor inventory availability', 'CRM activity feed'],
  },
  'Recon Manager': {
    description: 'Full visibility into the reconditioning workflow across every vehicle.',
    features: ['Recon pipeline by step', 'Technician workload & assignments', 'Vehicles stalled in recon', 'Average cycle time tracking', 'Vendor coordination', 'Before/after photo review'],
  },
  'Service Advisor': {
    description: 'Service department intake, scheduling, and customer vehicle status.',
    features: ['Today\'s service appointments', 'Customer check-in queue', 'RO status by vehicle', 'Courtesy vehicle assignments', 'Estimated completion times', 'Parts availability alerts'],
  },
  'Detail Team': {
    description: 'Detail queue management and assignment coordination for the team.',
    features: ['Detail queue by priority', 'Team member assignments', 'Vehicle wash & detail status', 'Customer delivery prep queue', 'Lot readiness checklist', 'Supply level tracking'],
  },
}

export default function PlaceholderDashboard({ role }: { role: string }) {
  const meta = roleMeta[role] ?? { description: 'Dashboard coming soon.', features: [] }

  return (
    <div className="flex-1 flex items-center justify-center px-6">
      <div className="max-w-md text-center">
        <div className="w-16 h-16 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center mx-auto mb-5">
          <svg width="28" height="28" fill="none" viewBox="0 0 24 24">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="#2563EB" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <h2 className="text-[22px] font-bold text-slate-900 mb-2">{role} Dashboard</h2>
        <p className="text-[14px] text-slate-500 mb-6 leading-relaxed">{meta.description}</p>

        {meta.features.length > 0 && (
          <div className="text-left bg-white rounded-2xl border border-slate-200 p-5 mb-6">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-3">Planned Features</div>
            <ul className="space-y-2">
              {meta.features.map(f => (
                <li key={f} className="flex items-center gap-2.5 text-[13px] text-slate-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="inline-flex items-center gap-2 text-[12px] font-semibold text-blue-600 bg-blue-50 border border-blue-200 px-4 py-2 rounded-full">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
          In Development
        </div>
      </div>
    </div>
  )
}
