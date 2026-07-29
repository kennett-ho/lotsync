import { useState } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

type TabId =
  | "daily-summary"
  | "vehicle-movement"
  | "dealer-trades"
  | "task-completion"
  | "request-volume"
  | "inventory-age"
  | "exception-trends";

type DateFilter = "today" | "week" | "month";

// ─── BarChart ────────────────────────────────────────────────────────────────

function BarChart({
  data,
  labels,
  color = "#3B82F6",
  height = 80,
}: {
  data: number[];
  labels: string[];
  color?: string;
  height?: number;
}) {
  const max = Math.max(...data);
  return (
    <svg width="100%" height={height} className="overflow-visible">
      {data.map((val, i) => {
        const barH = (val / max) * (height - 20);
        const x = (i / data.length) * 100;
        const w = (1 / data.length) * 100 - 1.5;
        return (
          <g key={i}>
            <rect
              x={`${x}%`}
              y={height - 20 - barH}
              width={`${w}%`}
              height={barH}
              rx="3"
              fill={color}
              opacity="0.85"
            />
            <text
              x={`${x + w / 2}%`}
              y={height - 4}
              textAnchor="middle"
              fontSize="9"
              fill="#94a3b8"
            >
              {labels[i]}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ─── StatCard ────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  color = "text-slate-800",
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-4">
      <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-[24px] font-bold ${color}`}>{value}</p>
      {sub && <p className="text-[11px] text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

// ─── ChartCard ───────────────────────────────────────────────────────────────

function ChartCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-5">
      <p className="text-[12px] font-semibold text-slate-600 mb-4">{title}</p>
      {children}
    </div>
  );
}

// ─── Table ───────────────────────────────────────────────────────────────────

function Table({
  headers,
  rows,
}: {
  headers: string[];
  rows: (string | number)[][];
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-100 overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-100">
            {headers.map((h, i) => (
              <th
                key={i}
                className="text-left text-[11px] font-semibold text-slate-400 uppercase tracking-wide px-4 py-3"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} className="border-b border-slate-50 last:border-0 hover:bg-slate-50 transition-colors">
              {row.map((cell, ci) => (
                <td key={ci} className="px-4 py-3 text-[12px] text-slate-700">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Tab Content ─────────────────────────────────────────────────────────────

function DailySummary() {
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Vehicles Processed" value="1,247" sub="+2.3% vs yesterday" />
        <StatCard label="Tasks Completed" value="23" sub="of 27 assigned" />
        <StatCard label="Requests Handled" value="8" sub="2 pending" />
        <StatCard label="Exceptions" value="12" color="text-red-600" sub="8 resolved" />
      </div>
      <ChartCard title="Vehicles Processed — Last 7 Days">
        <BarChart
          data={[1180, 1234, 1198, 1247, 1265, 1231, 1247]}
          labels={["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
          color="#3B82F6"
          height={100}
        />
      </ChartCard>
      <Table
        headers={["Department", "Tasks", "Requests", "Exceptions"]}
        rows={[
          ["Lot Operations", 10, 3, 5],
          ["Service", 6, 2, 4],
          ["Sales", 4, 2, 2],
          ["Recon", 3, 1, 1],
        ]}
      />
    </div>
  );
}

function VehicleMovement() {
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Total Moves" value="34" sub="today" />
        <StatCard label="Avg Time" value="18 min" sub="per move" />
        <StatCard label="Completed" value="31" sub="3 in progress" color="text-emerald-700" />
      </div>
      <ChartCard title="Moves Per Hour (8 AM – 3 PM)">
        <BarChart
          data={[3, 5, 8, 6, 4, 7, 4, 2]}
          labels={["8A", "9A", "10A", "11A", "12P", "1P", "2P", "3P"]}
          color="#6366F1"
          height={100}
        />
      </ChartCard>
      <Table
        headers={["Type", "Count", "Avg Duration", "Completed"]}
        rows={[
          ["Lot Move", 12, "15 min", 11],
          ["Service Pull", 8, "12 min", 8],
          ["Showroom", 4, "22 min", 4],
          ["Staging", 6, "18 min", 5],
          ["Dealer Trade", 4, "45 min", 3],
        ]}
      />
    </div>
  );
}

function DealerTrades() {
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Active" value="4" sub="in progress" color="text-orange-600" />
        <StatCard label="Completed Today" value="2" sub="on time" color="text-emerald-700" />
        <StatCard label="Total Vehicles" value="11" sub="across all trades" />
      </div>
      <ChartCard title="Vehicles by Trade Type">
        <BarChart
          data={[5, 3, 2, 1]}
          labels={["Incoming", "Outgoing", "Swap", "Pending"]}
          color="#F97316"
          height={80}
        />
      </ChartCard>
      <Table
        headers={["Trade ID", "Partner", "Vehicles", "Status", "Staff"]}
        rows={[
          ["DT-0142", "AutoNation BMW", 3, "In Transit", "Jordan Davis"],
          ["DT-0141", "Hendrick Honda", 2, "Completed", "Rosa Pereira"],
          ["DT-0140", "Lithia Ford", 4, "Completed", "Jordan Davis"],
          ["DT-0143", "Serra Mazda", 2, "Pending Approval", "Rosa Pereira"],
        ]}
      />
    </div>
  );
}

function TaskCompletion() {
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Assigned" value="27" />
        <StatCard label="Completed" value="23" color="text-emerald-700" />
        <StatCard label="In Progress" value="3" color="text-blue-700" />
        <StatCard label="Overdue" value="1" color="text-red-600" />
      </div>
      <ChartCard title="Tasks Completed Per Hour">
        <BarChart
          data={[1, 3, 5, 4, 6, 3, 1]}
          labels={["8A", "9A", "10A", "11A", "12P", "1P", "2P"]}
          color="#10B981"
          height={100}
        />
      </ChartCard>
      <Table
        headers={["Department", "Assigned", "Completed", "In Progress", "Overdue"]}
        rows={[
          ["Lot Operations", 12, 10, 2, 0],
          ["Service", 8, 7, 1, 0],
          ["Recon", 4, 3, 0, 1],
          ["Sales", 3, 3, 0, 0],
        ]}
      />
    </div>
  );
}

function RequestVolume() {
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Total Requests" value="34" />
        <StatCard label="Handled" value="26" color="text-emerald-700" />
        <StatCard label="Pending" value="6" color="text-amber-600" />
        <StatCard label="Avg Response" value="8 min" />
      </div>
      <ChartCard title="Request Volume by Hour">
        <BarChart
          data={[2, 4, 6, 8, 5, 6, 3]}
          labels={["8A", "9A", "10A", "11A", "12P", "1P", "2P"]}
          color="#8B5CF6"
          height={100}
        />
      </ChartCard>
      <Table
        headers={["Department", "Requests", "Handled", "Pending", "Avg Time"]}
        rows={[
          ["Service", 14, 11, 3, "6 min"],
          ["Sales", 10, 8, 2, "9 min"],
          ["Lot Operations", 7, 5, 1, "11 min"],
          ["Recon", 3, 2, 0, "7 min"],
        ]}
      />
    </div>
  );
}

function InventoryAge() {
  const segments = [
    { label: "0–30 days", count: 180, color: "#10B981", bg: "bg-emerald-500" },
    { label: "31–60 days", count: 85, color: "#F59E0B", bg: "bg-amber-400" },
    { label: "61–90 days", count: 35, color: "#F97316", bg: "bg-orange-500" },
    { label: "90+ days", count: 12, color: "#EF4444", bg: "bg-red-500" },
  ];
  const total = segments.reduce((a, s) => a + s.count, 0);

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Avg Days on Lot" value="28d" />
        <StatCard label="Over 60 Days" value="47 vehicles" color="text-orange-600" />
        <StatCard label="Freshest" value="2d" color="text-emerald-700" />
        <StatCard label="Oldest" value="91d" color="text-red-600" />
      </div>

      <div className="bg-white rounded-xl border border-slate-100 p-5">
        <p className="text-[12px] font-semibold text-slate-600 mb-4">Inventory Age Distribution ({total} vehicles)</p>
        {/* Stacked bar */}
        <div className="flex w-full h-8 rounded-xl overflow-hidden gap-0.5 mb-4">
          {segments.map((s) => (
            <div
              key={s.label}
              className={`${s.bg} h-full transition-all`}
              style={{ width: `${(s.count / total) * 100}%` }}
              title={`${s.label}: ${s.count}`}
            />
          ))}
        </div>
        <div className="flex items-center gap-5 flex-wrap">
          {segments.map((s) => (
            <div key={s.label} className="flex items-center gap-1.5">
              <div className={`w-2.5 h-2.5 rounded-sm ${s.bg}`} />
              <span className="text-[11px] text-slate-600">
                {s.label} — <span className="font-semibold">{s.count}</span>
              </span>
            </div>
          ))}
        </div>
      </div>

      <Table
        headers={["Stock #", "Year", "Make / Model", "Days on Lot", "Status"]}
        rows={[
          ["F29917", "2022", "Ford F-150", "91d", "Needs Attention"],
          ["H64509", "2021", "Honda CR-V", "88d", "Needs Attention"],
          ["D72044", "2023", "Dodge Durango", "76d", "Aging"],
          ["G11203", "2022", "GMC Sierra", "74d", "Aging"],
          ["M29481", "2021", "Mazda CX-5", "68d", "Aging"],
          ["A48291", "2023", "Accord Sport", "64d", "Aging"],
          ["C84711", "2022", "Chevy Tahoe", "62d", "Aging"],
          ["E51388", "2024", "BMW 5 Series", "58d", "Watch"],
          ["B10293", "2023", "BMW 3 Series", "55d", "Watch"],
          ["K30471", "2022", "Kia Sorento", "51d", "Watch"],
        ]}
      />
    </div>
  );
}

function ExceptionTrends() {
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Today" value="12" color="text-red-600" />
        <StatCard label="Resolved" value="8" color="text-emerald-700" />
        <StatCard label="Auto-Resolved" value="4" color="text-blue-700" />
        <StatCard label="Recurring" value="3" color="text-orange-600" />
      </div>
      <ChartCard title="Exceptions — Last 7 Days">
        <BarChart
          data={[8, 11, 9, 14, 10, 7, 12]}
          labels={["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
          color="#EF4444"
          height={100}
        />
      </ChartCard>
      <Table
        headers={["Exception Type", "Count", "Resolved", "Auto-Resolved", "Recurring"]}
        rows={[
          ["Vehicle Not Found", 4, 3, 1, 1],
          ["Task Overdue", 3, 2, 1, 1],
          ["Key Not Returned", 2, 1, 1, 0],
          ["Tracker Mismatch", 2, 1, 1, 1],
          ["Sync Failure", 1, 1, 0, 0],
        ]}
      />
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

const TABS: { id: TabId; label: string }[] = [
  { id: "daily-summary", label: "Daily Summary" },
  { id: "vehicle-movement", label: "Vehicle Movement" },
  { id: "dealer-trades", label: "Dealer Trades" },
  { id: "task-completion", label: "Task Completion" },
  { id: "request-volume", label: "Request Volume" },
  { id: "inventory-age", label: "Inventory Age" },
  { id: "exception-trends", label: "Exception Trends" },
];

function TabContent({ tab }: { tab: TabId }) {
  switch (tab) {
    case "daily-summary": return <DailySummary />;
    case "vehicle-movement": return <VehicleMovement />;
    case "dealer-trades": return <DealerTrades />;
    case "task-completion": return <TaskCompletion />;
    case "request-volume": return <RequestVolume />;
    case "inventory-age": return <InventoryAge />;
    case "exception-trends": return <ExceptionTrends />;
  }
}

export default function Reports(): JSX.Element {
  const [activeTab, setActiveTab] = useState<TabId>("daily-summary");
  const [dateFilter, setDateFilter] = useState<DateFilter>("today");

  return (
    <div className="h-full flex flex-col bg-slate-50 overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b border-slate-100 px-6 py-4">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-[18px] font-bold text-slate-800">Reports</h1>
            <p className="text-[12px] text-slate-400 mt-0.5">
              Management analytics and operational summaries
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Date filter */}
            <div className="flex items-center bg-slate-100 rounded-lg p-0.5">
              {(["today", "week", "month"] as DateFilter[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setDateFilter(f)}
                  className={`px-3 py-1.5 rounded-md text-[11px] font-medium transition-colors ${
                    dateFilter === f
                      ? "bg-white text-slate-800 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  {f === "today" ? "Today" : f === "week" ? "This Week" : "This Month"}
                </button>
              ))}
            </div>
            {/* Export */}
            <button className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 rounded-lg text-[12px] font-medium text-slate-600 hover:bg-slate-50 transition-colors">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Export
            </button>
          </div>
        </div>

        {/* Tab Nav */}
        <div className="flex items-center gap-0 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-[12px] font-medium whitespace-nowrap border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-blue-600 text-blue-700"
                  : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <TabContent tab={activeTab} />
      </div>
    </div>
  );
}
