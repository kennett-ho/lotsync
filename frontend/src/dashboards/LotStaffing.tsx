import { useState } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

type StaffStatus = "available" | "busy" | "dealer-trade" | "break" | "idle";

interface StaffMember {
  id: string;
  name: string;
  initials: string;
  avatarColor: string;
  title: string;
  status: StaffStatus;
  currentAssignment?: string;
  currentVehicle?: string;
  tasksToday: number;
  tasksCompleted: number;
  openRequests: number;
  hoursOnClock: string;
  zone: string;
  recentActivity: string[];
}

// ─── Data ────────────────────────────────────────────────────────────────────

const STAFF: StaffMember[] = [
  {
    id: "1",
    name: "Marcus Torres",
    initials: "MT",
    avatarColor: "#2563EB",
    title: "Lot Attendant",
    status: "busy",
    currentAssignment: "Service Pull — BMW 5 Series E51388",
    currentVehicle: "E51388",
    tasksToday: 6,
    tasksCompleted: 4,
    openRequests: 2,
    hoursOnClock: "4h 12m",
    zone: "Kia Front Lot",
    recentActivity: [
      "Pulled E51388 to Service Bay",
      "Installed RecovR on A48291",
      "Moved D72044 to Frontline",
    ],
  },
  {
    id: "2",
    name: "K. Williams",
    initials: "KW",
    avatarColor: "#7C3AED",
    title: "Lot Attendant",
    status: "busy",
    currentAssignment: "Fuel Run — 2 Trucks",
    tasksToday: 5,
    tasksCompleted: 3,
    openRequests: 1,
    hoursOnClock: "5h 30m",
    zone: "Truck Row",
    recentActivity: [
      "Fueling F29917",
      "Moved H64509 to Mazda Row",
      "Photos complete for D72044",
    ],
  },
  {
    id: "3",
    name: "Jordan Davis",
    initials: "JD",
    avatarColor: "#0891B2",
    title: "Lot Manager",
    status: "dealer-trade",
    currentAssignment: "Dealer Trade — AutoNation BMW",
    tasksToday: 8,
    tasksCompleted: 5,
    openRequests: 3,
    hoursOnClock: "6h 45m",
    zone: "Offsite",
    recentActivity: [
      "Departed for AutoNation BMW",
      "Confirmed trade paperwork",
      "Pre-departure checklist complete",
    ],
  },
  {
    id: "4",
    name: "Rosa Pereira",
    initials: "RP",
    avatarColor: "#6D28D9",
    title: "Tower Manager",
    status: "available",
    tasksToday: 12,
    tasksCompleted: 9,
    openRequests: 5,
    hoursOnClock: "7h 20m",
    zone: "Tower Office",
    recentActivity: [
      "Reviewed 3 trade requests",
      "Approved dealer trade DT-0142",
      "Updated staging assignments",
    ],
  },
  {
    id: "5",
    name: "Alex Chen",
    initials: "AC",
    avatarColor: "#059669",
    title: "Recon Tech",
    status: "busy",
    currentAssignment: "RapidRecon — Ford Explorer M29481",
    currentVehicle: "M29481",
    tasksToday: 4,
    tasksCompleted: 2,
    openRequests: 0,
    hoursOnClock: "3h 15m",
    zone: "Recon Bay",
    recentActivity: [
      "Started recon on M29481",
      "Completed inspection on G11203",
      "Submitted 2 recon reports",
    ],
  },
  {
    id: "6",
    name: "T. Rivera",
    initials: "TR",
    avatarColor: "#D97706",
    title: "Lot Attendant",
    status: "break",
    tasksToday: 3,
    tasksCompleted: 3,
    openRequests: 0,
    hoursOnClock: "4h 0m",
    zone: "Break Room",
    recentActivity: [
      "Completed all tasks",
      "Final delivery staged",
      "Zone sweep complete",
    ],
  },
];

const STATUS_CONFIG: Record<StaffStatus, { dot: string; text: string; label: string }> = {
  available: { dot: "bg-emerald-400", text: "text-emerald-700", label: "Available" },
  busy: { dot: "bg-blue-400", text: "text-blue-700", label: "Busy" },
  "dealer-trade": { dot: "bg-orange-400", text: "text-orange-700", label: "Dealer Trade" },
  break: { dot: "bg-slate-300", text: "text-slate-500", label: "On Break" },
  idle: { dot: "bg-amber-400", text: "text-amber-700", label: "Idle" },
};

// ─── Sub-components ──────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: StaffStatus }) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] font-medium ${cfg.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

function Avatar({ initials, color, size = 36 }: { initials: string; color: string; size?: number }) {
  return (
    <div
      className="rounded-full flex items-center justify-center text-white font-semibold flex-shrink-0"
      style={{ width: size, height: size, backgroundColor: color, fontSize: size * 0.35 }}
    >
      {initials}
    </div>
  );
}

function StaffCard({
  member,
  selected,
  onClick,
}: {
  member: StaffMember;
  selected: boolean;
  onClick: () => void;
}) {
  const pct = Math.round((member.tasksCompleted / member.tasksToday) * 100);
  return (
    <button
      onClick={onClick}
      className={`w-full text-left bg-white rounded-xl p-4 border transition-all ${
        selected ? "border-blue-500 ring-2 ring-blue-200" : "border-slate-100 hover:border-slate-200"
      }`}
    >
      <div className="flex items-start gap-3 mb-3">
        <Avatar initials={member.initials} color={member.avatarColor} size={40} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className="text-[13px] font-semibold text-slate-800 truncate">{member.name}</p>
            <StatusBadge status={member.status} />
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">{member.title}</p>
        </div>
      </div>

      {member.currentAssignment && (
        <div className="mb-3 px-2.5 py-1.5 bg-slate-50 rounded-lg border border-slate-100">
          <p className="text-[11px] text-slate-500 truncate">{member.currentAssignment}</p>
        </div>
      )}

      <div className="flex items-center gap-2 text-[11px] text-slate-500 mb-2">
        <span>
          <span className="font-medium text-slate-700">{member.tasksCompleted}</span>
          /{member.tasksToday} tasks
        </span>
        <span className="text-slate-200">·</span>
        <span>
          <span className="font-medium text-slate-700">{member.openRequests}</span> requests
        </span>
        <span className="text-slate-200">·</span>
        <span>{member.hoursOnClock}</span>
      </div>

      <div className="w-full bg-slate-100 rounded-full h-1 mb-3">
        <div className="bg-blue-500 h-1 rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>

      <div className="flex items-center justify-between">
        <span className="text-[11px] text-slate-400">{member.zone}</span>
        {(member.status === "available" || member.status === "idle") && (
          <span className="text-[11px] font-medium text-blue-600 px-2 py-0.5 bg-blue-50 rounded-md border border-blue-100">
            Quick Assign
          </span>
        )}
      </div>
    </button>
  );
}

function DetailPanel({ member }: { member: StaffMember }) {
  const pct = Math.round((member.tasksCompleted / member.tasksToday) * 100);
  return (
    <div className="flex flex-col gap-4">
      {/* Header card */}
      <div className="bg-white rounded-xl border border-slate-100 p-5">
        <div className="flex items-center gap-4">
          <Avatar initials={member.initials} color={member.avatarColor} size={56} />
          <div>
            <h3 className="text-[16px] font-bold text-slate-800">{member.name}</h3>
            <p className="text-[12px] text-slate-500">{member.title}</p>
            <div className="mt-1 flex items-center gap-2">
              <StatusBadge status={member.status} />
              <span className="text-[11px] text-slate-400">· {member.hoursOnClock} on clock</span>
            </div>
          </div>
        </div>
      </div>

      {/* Current Assignment */}
      {member.currentAssignment && (
        <div className="bg-white rounded-xl border border-slate-100 p-4">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-2">
            Current Assignment
          </p>
          <p className="text-[13px] font-medium text-slate-700">{member.currentAssignment}</p>
          {member.currentVehicle && (
            <span className="mt-2 inline-block text-[11px] font-semibold text-blue-700 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded-md">
              {member.currentVehicle}
            </span>
          )}
        </div>
      )}

      {/* Performance */}
      <div className="bg-white rounded-xl border border-slate-100 p-4">
        <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-3">
          Today's Performance
        </p>
        <div className="flex items-end justify-between mb-1">
          <span className="text-[12px] text-slate-600">Tasks Completed</span>
          <span className="text-[13px] font-bold text-slate-800">
            {member.tasksCompleted}/{member.tasksToday}
          </span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-1.5 mb-3">
          <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
        </div>
        <div className="flex items-center gap-2 text-[12px]">
          <span className="text-slate-500">Open Requests:</span>
          <span className="font-semibold text-slate-800">{member.openRequests}</span>
        </div>
      </div>

      {/* Zone */}
      <div className="bg-white rounded-xl border border-slate-100 p-4">
        <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-2">
          Zone & Location
        </p>
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="text-[13px] font-medium text-slate-700">{member.zone}</span>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl border border-slate-100 p-4">
        <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-3">
          Recent Activity
        </p>
        <div className="flex flex-col gap-0">
          {member.recentActivity.map((activity, i) => (
            <div key={i} className="flex items-start gap-3 relative pb-3 last:pb-0">
              <div className="flex flex-col items-center">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1 flex-shrink-0" />
                {i < member.recentActivity.length - 1 && (
                  <div className="w-px bg-slate-100 mt-1" style={{ minHeight: 24 }} />
                )}
              </div>
              <p className="text-[12px] text-slate-600">{activity}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button className="flex-1 py-2 text-[12px] font-semibold bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          Assign Task
        </button>
        <button className="flex-1 py-2 text-[12px] font-semibold border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50 transition-colors">
          Message
        </button>
        <button className="flex-1 py-2 text-[12px] font-semibold border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50 transition-colors">
          Full Activity
        </button>
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function LotStaffing(): JSX.Element {
  const [selectedId, setSelectedId] = useState<string>(STAFF[0].id);
  const selectedMember = STAFF.find((s) => s.id === selectedId) ?? STAFF[0];

  const counts = STAFF.reduce(
    (acc, s) => {
      if (s.status === "available" || s.status === "idle") acc.available++;
      else if (s.status === "busy" || s.status === "dealer-trade") acc.active++;
      else if (s.status === "break") acc.onBreak++;
      return acc;
    },
    { available: 0, active: 0, onBreak: 0 }
  );

  const activeCount = STAFF.filter((s) => s.status !== "break").length;

  return (
    <div className="h-full flex flex-col bg-slate-50 overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b border-slate-100 px-6 py-4">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h1 className="text-[18px] font-bold text-slate-800">Lot Staffing</h1>
            <p className="text-[12px] text-slate-400 mt-0.5">
              {activeCount} of {STAFF.length} employees active today
            </p>
          </div>
        </div>
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-1.5 text-[12px]">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="font-semibold text-slate-700">{counts.available}</span>
            <span className="text-slate-400">Available</span>
          </div>
          <div className="flex items-center gap-1.5 text-[12px]">
            <span className="w-2 h-2 rounded-full bg-blue-400" />
            <span className="font-semibold text-slate-700">{counts.active}</span>
            <span className="text-slate-400">Busy</span>
          </div>
          <div className="flex items-center gap-1.5 text-[12px]">
            <span className="w-2 h-2 rounded-full bg-slate-300" />
            <span className="font-semibold text-slate-700">{counts.onBreak}</span>
            <span className="text-slate-400">On Break</span>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Staff Grid (~60%) */}
        <div className="flex-[3] overflow-y-auto p-5">
          <div className="grid grid-cols-2 gap-3">
            {STAFF.map((member) => (
              <StaffCard
                key={member.id}
                member={member}
                selected={member.id === selectedId}
                onClick={() => setSelectedId(member.id)}
              />
            ))}
          </div>
        </div>

        {/* Right: Detail Panel (~40%) */}
        <div className="flex-[2] border-l border-slate-100 overflow-y-auto p-5 bg-slate-50">
          <DetailPanel member={selectedMember} />
        </div>
      </div>
    </div>
  );
}
