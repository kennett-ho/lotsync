import { useState, useMemo } from "react";

type RunId = "7:02 AM" | "12:31 PM";
type ExceptionStatus =
  | "pending"
  | "in-review"
  | "task-created"
  | "auto-resolved"
  | "resolved";

interface Exception {
  stock: string;
  year: number;
  make: string;
  model: string;
  issue: string;
  system: string;
  suggestedAction: string;
  status: ExceptionStatus;
}

const ALL_EXCEPTIONS: Exception[] = [
  {
    stock: "P28192",
    year: 2021,
    make: "Jeep",
    model: "Grand Cherokee",
    issue: "Vehicle not found in lot scan",
    system: "RecovR",
    suggestedAction: "Investigate physical location",
    status: "pending",
  },
  {
    stock: "A48291",
    year: 2023,
    make: "Honda",
    model: "Accord",
    issue: "Days in inventory discrepancy: DMS 38d vs LotSync 42d",
    system: "Tekion",
    suggestedAction: "Reconcile intake date",
    status: "in-review",
  },
  {
    stock: "E51388",
    year: 2023,
    make: "BMW",
    model: "5 Series",
    issue: "RecovR tracker not installed",
    system: "RecovR",
    suggestedAction: "Install tracker",
    status: "task-created",
  },
  {
    stock: "H72840",
    year: 2023,
    make: "Subaru",
    model: "Outback",
    issue: "Location discrepancy: DMS=lot, RecovR=offsite",
    system: "RecovR",
    suggestedAction: "Verify current location",
    status: "pending",
  },
  {
    stock: "C84711",
    year: 2022,
    make: "Ford",
    model: "F-150",
    issue: "Odometer value missing",
    system: "Tekion",
    suggestedAction: "Update mileage in Tekion",
    status: "pending",
  },
  {
    stock: "D72044",
    year: 2024,
    make: "Kia",
    model: "Telluride",
    issue: "Status mismatch: Tekion=In Transit, LotSync=Available",
    system: "Tekion",
    suggestedAction: "Verify status",
    status: "pending",
  },
  {
    stock: "G11203",
    year: 2024,
    make: "Hyundai",
    model: "Tucson",
    issue: "Duplicate VIN entry detected",
    system: "Tekion",
    suggestedAction: "Remove duplicate record",
    status: "auto-resolved",
  },
  {
    stock: "B93021",
    year: 2024,
    make: "Toyota",
    model: "Camry",
    issue: "Missing exterior color in Tekion record",
    system: "Tekion",
    suggestedAction: "Update vehicle details",
    status: "auto-resolved",
  },
  {
    stock: "F29917",
    year: 2022,
    make: "Chevrolet",
    model: "Silverado",
    issue: "Key tracking gap: no activity in 48h",
    system: "Keyper",
    suggestedAction: "Verify key status",
    status: "pending",
  },
  {
    stock: "G19283",
    year: 2022,
    make: "Toyota",
    model: "RAV4",
    issue: "Zone differs from physical scan by 2 zones",
    system: "RecovR",
    suggestedAction: "Update zone",
    status: "auto-resolved",
  },
  {
    stock: "M29481",
    year: 2022,
    make: "Ford",
    model: "Explorer",
    issue: "RapidRecon status stale (5 days)",
    system: "RapidRecon",
    suggestedAction: "Refresh recon status",
    status: "task-created",
  },
  {
    stock: "B39281",
    year: 2024,
    make: "Honda",
    model: "CR-V",
    issue: "MDD install date missing",
    system: "MDD",
    suggestedAction: "Update install record",
    status: "auto-resolved",
  },
];

const RUN_DATA: Record<
  RunId,
  {
    vehiclesProcessed: number;
    exceptions: number;
    autoResolved: number;
    tasksGenerated: number;
    exceptionIndices: number[];
  }
> = {
  "12:31 PM": {
    vehiclesProcessed: 1251,
    exceptions: 3,
    autoResolved: 0,
    tasksGenerated: 18,
    exceptionIndices: [0, 1, 2],
  },
  "7:02 AM": {
    vehiclesProcessed: 1247,
    exceptions: 12,
    autoResolved: 4,
    tasksGenerated: 8,
    exceptionIndices: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
  },
};

const RUN_HISTORY = [
  { label: "Today 12:31 PM", exceptions: 3 },
  { label: "Today 7:02 AM", exceptions: 12 },
  { label: "Yesterday 6:01 PM", exceptions: 1 },
  { label: "Yesterday 12:30 PM", exceptions: 7 },
  { label: "Yesterday 7:01 AM", exceptions: 2 },
];

const SYSTEMS = [
  {
    name: "Tekion",
    status: "connected",
    detail: "API v3.2 · 1,247 vehicles synced",
  },
  { name: "Keyper", status: "connected", detail: "384 keys tracked" },
  {
    name: "RecovR",
    status: "partial",
    detail: "312 of 347 vehicles tracked · 35 missing",
  },
  { name: "MDD", status: "connected", detail: "89 installations synced" },
  {
    name: "RapidRecon",
    status: "connected",
    detail: "23 vehicles in recon pipeline",
  },
];

function statusPillClass(status: ExceptionStatus): string {
  switch (status) {
    case "pending":
      return "bg-amber-50 text-amber-700 border border-amber-200";
    case "in-review":
      return "bg-blue-50 text-blue-700 border border-blue-200";
    case "task-created":
      return "bg-violet-50 text-violet-700 border border-violet-200";
    case "auto-resolved":
      return "bg-emerald-50 text-emerald-700 border border-emerald-200";
    case "resolved":
      return "bg-slate-100 text-slate-600 border border-slate-200";
  }
}

function statusPillLabel(status: ExceptionStatus): string {
  switch (status) {
    case "pending":
      return "Pending";
    case "in-review":
      return "In Review";
    case "task-created":
      return "Task Created";
    case "auto-resolved":
      return "Auto-Resolved";
    case "resolved":
      return "Resolved";
  }
}

function SystemDot({ status }: { status: string }) {
  if (status === "connected")
    return (
      <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
    );
  if (status === "partial")
    return (
      <span className="inline-block w-2 h-2 rounded-full bg-amber-400 shrink-0" />
    );
  return (
    <span className="inline-block w-2 h-2 rounded-full bg-slate-300 shrink-0" />
  );
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="15"
      height="15"
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M13.65 2.35A8 8 0 1 0 15 8h-2a6 6 0 1 1-1.76-4.24L9 6h6V0l-1.35 2.35Z"
        fill="currentColor"
      />
    </svg>
  );
}

function SyncIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="13"
      height="13"
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M11.44 2.56A6 6 0 1 0 13 7h-1.5A4.5 4.5 0 1 1 10.06 3.94L8.5 5.5H13V1l-1.56 1.56Z"
        fill="currentColor"
      />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="7" cy="7" r="6.5" stroke="currentColor" />
      <path
        d="M4 7l2 2 4-4"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="7" cy="7" r="6.5" stroke="currentColor" />
      <path
        d="M7 4v3.5l2 1.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="13"
      height="13"
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.3" />
      <path
        d="M9.5 9.5L12.5 12.5"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}

function TaskIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="13"
      height="13"
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect
        x="1.5"
        y="1.5"
        width="11"
        height="11"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.3"
      />
      <path
        d="M4 7h6M4 4.5h6M4 9.5h4"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}

function LightbulbIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="13"
      height="13"
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M7 1a4 4 0 0 0-2 7.46V10h4V8.46A4 4 0 0 0 7 1Z"
        stroke="currentColor"
        strokeWidth="1.3"
      />
      <path
        d="M5 10h4M5.5 12h3"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="13"
      height="13"
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M7 1.5L13 12.5H1L7 1.5Z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
      <path
        d="M7 5.5v3M7 10.5v.5"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}

function AutoResolveIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="13"
      height="13"
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M4 7.5l2 2 4-4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

export default function InventorySync(): JSX.Element {
  const [activeRun, setActiveRun] = useState<RunId>("12:31 PM");
  const [search, setSearch] = useState("");

  const runData = RUN_DATA[activeRun];

  const exceptions = useMemo(
    () => runData.exceptionIndices.map((i) => ALL_EXCEPTIONS[i]),
    [runData]
  );

  const filtered = useMemo(() => {
    if (!search.trim()) return exceptions;
    const q = search.toLowerCase();
    return exceptions.filter(
      (e) =>
        e.stock.toLowerCase().includes(q) ||
        e.make.toLowerCase().includes(q) ||
        e.model.toLowerCase().includes(q) ||
        e.issue.toLowerCase().includes(q) ||
        e.system.toLowerCase().includes(q)
    );
  }, [exceptions, search]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Page Header */}
      <div className="bg-white border-b border-slate-100 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-[22px] font-bold text-slate-900 leading-tight">
              Inventory Sync
            </h1>
            <p className="text-[13px] text-slate-500 mt-0.5">
              Automated data reconciliation across all connected systems
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-[12px] text-slate-500">
              <SyncIcon className="text-slate-400" />
              <span>Last sync 2 min ago</span>
            </div>
            <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-[13px] font-medium px-4 py-2 rounded-xl transition-colors">
              <RefreshIcon />
              Run Sync Now
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 px-6 py-5 flex flex-col gap-5">
        {/* Sync Run Selector */}
        <div className="bg-white rounded-2xl border border-slate-100 p-4">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Today's Sync Runs
          </p>
          <div className="flex items-center gap-2">
            {(["7:02 AM", "12:31 PM"] as RunId[]).map((run) => {
              const data = RUN_DATA[run];
              const isActive = activeRun === run;
              return (
                <button
                  key={run}
                  onClick={() => setActiveRun(run)}
                  className={`flex items-center gap-2.5 px-4 py-2.5 rounded-xl border text-[13px] transition-all ${
                    isActive
                      ? "border-blue-200 bg-blue-50 text-blue-700"
                      : "border-slate-100 bg-white text-slate-600 hover:border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  <CheckCircleIcon
                    className={isActive ? "text-blue-500" : "text-emerald-500"}
                  />
                  <span className="font-semibold">{run}</span>
                  <span
                    className={`text-[11px] ${isActive ? "text-blue-500" : "text-slate-400"}`}
                  >
                    {data.vehiclesProcessed.toLocaleString()} vehicles
                  </span>
                  {data.exceptions > 0 && (
                    <span
                      className={`text-[11px] font-medium px-1.5 py-0.5 rounded-md ${
                        isActive
                          ? "bg-amber-100 text-amber-700"
                          : "bg-amber-50 text-amber-600"
                      }`}
                    >
                      {data.exceptions} exc
                    </span>
                  )}
                </button>
              );
            })}
            {/* Scheduled — disabled */}
            <button
              disabled
              className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl border border-slate-100 bg-slate-50 text-slate-400 text-[13px] cursor-not-allowed"
            >
              <ClockIcon className="text-slate-300" />
              <span className="font-semibold">6:00 PM</span>
              <span className="text-[11px]">Scheduled</span>
            </button>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-4 gap-4">
          {[
            {
              label: "Vehicles Processed",
              value: runData.vehiclesProcessed.toLocaleString(),
              color: "text-blue-600",
            },
            {
              label: "Exceptions",
              value: runData.exceptions,
              color: "text-amber-600",
            },
            {
              label: "Auto-Resolved",
              value: runData.autoResolved,
              color: "text-emerald-600",
            },
            {
              label: "Tasks Generated",
              value: runData.tasksGenerated,
              color: "text-slate-700",
            },
          ].map((stat) => (
            <div
              key={stat.label}
              className="bg-white rounded-2xl border border-slate-100 px-5 py-4"
            >
              <p className="text-[12px] text-slate-500 mb-1">{stat.label}</p>
              <p className={`text-[28px] font-bold leading-none ${stat.color}`}>
                {stat.value}
              </p>
            </div>
          ))}
        </div>

        {/* Two-column body */}
        <div className="flex gap-5 items-start pb-8">
          {/* Left: exceptions table (60%) */}
          <div className="flex-[3] min-w-0">
            <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
              {/* Table toolbar */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
                <div className="flex items-center gap-2.5">
                  <h2 className="text-[15px] font-semibold text-slate-900">
                    Exceptions
                  </h2>
                  <span className="bg-amber-100 text-amber-700 text-[11px] font-semibold px-2 py-0.5 rounded-full">
                    {exceptions.length}
                  </span>
                </div>
                <div className="relative">
                  <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search exceptions…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-8 pr-3 py-1.5 text-[12px] border border-slate-200 rounded-lg bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 w-52 text-slate-700 placeholder-slate-400"
                  />
                </div>
              </div>

              {/* Scrollable table */}
              <div className="overflow-y-auto" style={{ maxHeight: "440px" }}>
                <table className="w-full text-[12px]">
                  <thead className="sticky top-0 bg-slate-50 z-10">
                    <tr className="border-b border-slate-100">
                      <th className="text-left px-4 py-2.5 font-semibold text-slate-500 text-[11px] uppercase tracking-wider whitespace-nowrap">
                        Vehicle
                      </th>
                      <th className="text-left px-4 py-2.5 font-semibold text-slate-500 text-[11px] uppercase tracking-wider">
                        Issue
                      </th>
                      <th className="text-left px-4 py-2.5 font-semibold text-slate-500 text-[11px] uppercase tracking-wider whitespace-nowrap">
                        System
                      </th>
                      <th className="text-left px-4 py-2.5 font-semibold text-slate-500 text-[11px] uppercase tracking-wider whitespace-nowrap">
                        Suggested Action
                      </th>
                      <th className="text-left px-4 py-2.5 font-semibold text-slate-500 text-[11px] uppercase tracking-wider whitespace-nowrap">
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.length === 0 ? (
                      <tr>
                        <td
                          colSpan={5}
                          className="text-center py-10 text-slate-400 text-[13px]"
                        >
                          No exceptions match your search.
                        </td>
                      </tr>
                    ) : (
                      filtered.map((ex, idx) => (
                        <tr
                          key={ex.stock + idx}
                          className={`border-b border-slate-50 last:border-0 ${
                            idx % 2 === 0 ? "bg-white" : "bg-slate-50/50"
                          } ${ex.status === "pending" ? "border-l-2 border-l-amber-400" : "border-l-2 border-l-transparent"}`}
                        >
                          <td className="px-4 py-3 align-top whitespace-nowrap">
                            <span className="font-mono text-[11px] text-slate-500 block">
                              {ex.stock}
                            </span>
                            <span className="text-[12px] text-slate-800 font-medium whitespace-nowrap">
                              {ex.year} {ex.make} {ex.model}
                            </span>
                          </td>
                          <td className="px-4 py-3 align-top">
                            <span className="text-slate-700 leading-snug block">
                              {ex.issue}
                            </span>
                          </td>
                          <td className="px-4 py-3 align-top whitespace-nowrap">
                            <span className="bg-slate-100 text-slate-600 text-[11px] font-medium px-2 py-0.5 rounded-md">
                              {ex.system}
                            </span>
                          </td>
                          <td className="px-4 py-3 align-top text-slate-600 leading-snug">
                            {ex.suggestedAction}
                          </td>
                          <td className="px-4 py-3 align-top whitespace-nowrap">
                            <span
                              className={`inline-block text-[11px] font-medium px-2 py-0.5 rounded-full ${statusPillClass(ex.status)}`}
                            >
                              {statusPillLabel(ex.status)}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Right column (40%) */}
          <div className="flex-[2] min-w-0 flex flex-col gap-4">
            {/* System Status */}
            <div className="bg-white rounded-2xl border border-slate-100">
              <div className="px-5 py-4 border-b border-slate-100">
                <h2 className="text-[15px] font-semibold text-slate-900">
                  System Status
                </h2>
              </div>
              <div className="divide-y divide-slate-50">
                {SYSTEMS.map((sys) => (
                  <div key={sys.name} className="px-5 py-3 flex items-start gap-3">
                    <div className="mt-1.5">
                      <SystemDot status={sys.status} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] font-semibold text-slate-800">
                          {sys.name}
                        </span>
                        <span
                          className={`text-[11px] font-medium ${
                            sys.status === "connected"
                              ? "text-emerald-600"
                              : "text-amber-600"
                          }`}
                        >
                          {sys.status === "connected" ? "Connected" : "Partial"}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">
                        {sys.detail}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Detected Changes */}
            <div className="bg-white rounded-2xl border border-slate-100">
              <div className="px-5 py-4 border-b border-slate-100">
                <h2 className="text-[15px] font-semibold text-slate-900">
                  Detected Changes
                </h2>
              </div>
              <div className="px-5 py-4 flex flex-col gap-3">
                <div className="flex items-center gap-3">
                  <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-blue-50 text-blue-600 shrink-0">
                    <TaskIcon />
                  </span>
                  <span className="text-[13px] font-semibold text-slate-800">
                    {runData.tasksGenerated} new tasks generated
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-amber-50 text-amber-500 shrink-0">
                    <LightbulbIcon />
                  </span>
                  <span className="text-[13px] text-slate-700">
                    5 recommendations surfaced
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-amber-50 text-amber-600 shrink-0">
                    <WarningIcon />
                  </span>
                  <span className="text-[13px] text-slate-700">
                    {runData.exceptions} exceptions detected total
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 shrink-0">
                    <AutoResolveIcon />
                  </span>
                  <span className="text-[13px] text-slate-700">
                    {runData.autoResolved} resolved automatically
                  </span>
                </div>
              </div>
            </div>

            {/* Run History */}
            <div className="bg-white rounded-2xl border border-slate-100">
              <div className="px-5 py-4 border-b border-slate-100">
                <h2 className="text-[15px] font-semibold text-slate-900">
                  Run History
                </h2>
              </div>
              <div className="divide-y divide-slate-50">
                {RUN_HISTORY.map((run, idx) => (
                  <div
                    key={idx}
                    className="px-5 py-2.5 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                      <span className="text-[12px] text-slate-700">
                        {run.label}
                      </span>
                    </div>
                    <span
                      className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
                        run.exceptions > 5
                          ? "bg-amber-50 text-amber-600"
                          : run.exceptions > 0
                          ? "bg-slate-100 text-slate-500"
                          : "bg-emerald-50 text-emerald-600"
                      }`}
                    >
                      {run.exceptions} exc
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
