import { useState } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

type SectionId =
  | "profile"
  | "notifications"
  | "appearance"
  | "security"
  | "current-session"
  | "recent-activity";

// ─── Toggle Component ─────────────────────────────────────────────────────────

function Toggle({ on, onChange }: { on: boolean; onChange: () => void }) {
  return (
    <button
      onClick={onChange}
      className={`w-9 h-5 rounded-full transition-colors ${on ? "bg-blue-600" : "bg-slate-200"} relative flex-shrink-0`}
    >
      <span
        className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-all ${
          on ? "left-4" : "left-0.5"
        }`}
      />
    </button>
  );
}

// ─── Section: Profile ────────────────────────────────────────────────────────

function ProfileSection() {
  const [displayName, setDisplayName] = useState("");
  const [phone, setPhone] = useState("");
  const [zone, setZone] = useState("");

  return (
    <div className="flex flex-col gap-5">
      {/* Avatar card -- generic icon, no demo identity. Populated from the
          fields below once entered; blank fields show a neutral placeholder
          instead of fabricated demo data. */}
      <div className="bg-white rounded-xl border border-slate-100 p-5">
        <div className="flex items-center gap-4 mb-4">
          <div
            className="w-14 h-14 rounded-full flex items-center justify-center text-white flex-shrink-0"
            style={{ backgroundColor: "#64748B" }}
          >
            <svg width="24" height="24" fill="none" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/><circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="1.75"/></svg>
          </div>
          <div>
            <p className="text-[15px] font-bold text-slate-800">{displayName || "Name not set"}</p>
            <p className="text-[12px] text-slate-500">Lot Operations</p>
            <p className="text-[11px] text-slate-400 mt-0.5">LotSync</p>
          </div>
        </div>
      </div>

      {/* Edit form */}
      <div className="bg-white rounded-xl border border-slate-100 p-5">
        <p className="text-[12px] font-semibold text-slate-600 mb-4">Edit Profile</p>
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1.5">Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Your name"
              className="w-full px-3 py-2 text-[13px] border border-slate-200 rounded-lg bg-white text-slate-800 placeholder:text-slate-300 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1.5">Phone</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="(555) 555-5555"
              className="w-full px-3 py-2 text-[13px] border border-slate-200 rounded-lg bg-white text-slate-800 placeholder:text-slate-300 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1.5">Employee ID</label>
            <input
              type="text"
              value="—"
              readOnly
              className="w-full px-3 py-2 text-[13px] border border-slate-100 rounded-lg bg-slate-50 text-slate-400 cursor-not-allowed"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1.5">Default Zone</label>
            <input
              type="text"
              value={zone}
              onChange={(e) => setZone(e.target.value)}
              placeholder="e.g. Front Lot"
              className="w-full px-3 py-2 text-[13px] border border-slate-200 rounded-lg bg-white text-slate-800 placeholder:text-slate-300 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all"
            />
          </div>
          <button className="mt-1 self-start px-5 py-2 bg-blue-600 text-white text-[13px] font-semibold rounded-lg hover:bg-blue-700 transition-colors">
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Section: Notifications ──────────────────────────────────────────────────

interface NotifRow {
  id: string;
  label: string;
  description: string;
  on: boolean;
}

const NOTIFS_DEFAULT: NotifRow[] = [
  { id: "dealer-trade", label: "Dealer Trade Assigned", description: "When a dealer trade is assigned to you", on: true },
  { id: "recovr-verify", label: "RecovR Tracker Verified", description: "When a tracker is confirmed on a vehicle", on: true },
  { id: "inventory-sync", label: "Inventory Sync Finished", description: "When nightly or manual syncs complete", on: true },
  { id: "vehicle-not-found", label: "Vehicle Not Found", description: "Exception raised for missing inventory", on: true },
  { id: "keys-long", label: "Keys Checked Out 6+ Hours", description: "Alert when keys are out past threshold", on: false },
  { id: "task-overdue", label: "Task Overdue", description: "When an assigned task misses its deadline", on: true },
  { id: "new-request", label: "New Request Assigned to Me", description: "Direct requests from service or sales", on: true },
  { id: "morning-sync", label: "Morning Sync Complete", description: "Daily morning inventory sync summary", on: false },
];

function NotificationsSection() {
  const [notifs, setNotifs] = useState<NotifRow[]>(NOTIFS_DEFAULT);

  const toggle = (id: string) => {
    setNotifs((prev) => prev.map((n) => (n.id === id ? { ...n, on: !n.on } : n)));
  };

  return (
    <div className="bg-white rounded-xl border border-slate-100 overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100">
        <p className="text-[13px] font-semibold text-slate-700">Notification Preferences</p>
        <p className="text-[11px] text-slate-400 mt-0.5">Manage which events send you alerts</p>
      </div>
      <div className="divide-y divide-slate-50">
        {notifs.map((n) => (
          <div key={n.id} className="flex items-center justify-between gap-4 px-5 py-3.5">
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-medium text-slate-700">{n.label}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">{n.description}</p>
            </div>
            <Toggle on={n.on} onChange={() => toggle(n.id)} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Section: Appearance ─────────────────────────────────────────────────────

function AppearanceSection() {
  const [theme, setTheme] = useState<"light" | "dark" | "system">("light");
  const [density, setDensity] = useState<"comfortable" | "compact">("comfortable");

  return (
    <div className="flex flex-col gap-4">
      <div className="bg-white rounded-xl border border-slate-100 p-5">
        <p className="text-[12px] font-semibold text-slate-600 mb-3">Theme</p>
        <div className="flex items-center gap-2">
          {(["light", "dark", "system"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className={`px-4 py-2 rounded-lg text-[12px] font-medium transition-colors border ${
                theme === t
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
              }`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <div className="bg-white rounded-xl border border-slate-100 p-5">
        <p className="text-[12px] font-semibold text-slate-600 mb-3">Density</p>
        <div className="flex items-center gap-2">
          {(["comfortable", "compact"] as const).map((d) => (
            <button
              key={d}
              onClick={() => setDensity(d)}
              className={`px-4 py-2 rounded-lg text-[12px] font-medium transition-colors border ${
                density === d
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
              }`}
            >
              {d.charAt(0).toUpperCase() + d.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <div className="bg-slate-50 rounded-xl border border-slate-100 px-5 py-4">
        <p className="text-[12px] text-slate-400">Additional appearance settings coming soon.</p>
      </div>
    </div>
  );
}

// ─── Section: Security ───────────────────────────────────────────────────────

function SecuritySection() {
  return (
    <div className="flex flex-col gap-4">
      <div className="bg-white rounded-xl border border-slate-100 p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[13px] font-semibold text-slate-700">Password</p>
            <p className="text-[11px] text-slate-400 mt-0.5">Last changed 3 months ago</p>
          </div>
          <button className="px-3 py-1.5 text-[12px] font-medium border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 transition-colors">
            Change Password
          </button>
        </div>
      </div>
      <div className="bg-white rounded-xl border border-slate-100 p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[13px] font-semibold text-slate-700">Two-Factor Authentication</p>
            <p className="text-[11px] text-slate-400 mt-0.5">Not enabled</p>
          </div>
          <button className="px-3 py-1.5 text-[12px] font-semibold bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Enable
          </button>
        </div>
      </div>
      <div className="bg-white rounded-xl border border-slate-100 p-5">
        <p className="text-[13px] font-semibold text-slate-700">Active Sessions</p>
        <p className="text-[24px] font-bold text-slate-800 mt-1">1</p>
        <p className="text-[11px] text-slate-400">active session across devices</p>
      </div>
    </div>
  );
}

// ─── Section: Current Session ────────────────────────────────────────────────

function CurrentSessionSection() {
  return (
    <div className="flex flex-col gap-4">
      <div className="bg-white rounded-xl border border-slate-100 p-5">
        <p className="text-[12px] font-semibold text-slate-600 mb-4">Current Session</p>
        <div className="grid grid-cols-2 gap-4 mb-4">
          {[
            { label: "Device", value: "MacBook Pro 16″" },
            { label: "Browser", value: "Chrome 123" },
            { label: "IP Address", value: "192.168.1.42" },
            { label: "Location", value: "—" },
            { label: "Started", value: "Today 7:02 AM" },
            { label: "Duration", value: "3h 28m" },
          ].map(({ label, value }) => (
            <div key={label}>
              <p className="text-[11px] text-slate-400">{label}</p>
              <p className="text-[13px] font-medium text-slate-700 mt-0.5">{value}</p>
            </div>
          ))}
        </div>
        <button className="px-4 py-2 text-[12px] font-semibold border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition-colors">
          Sign Out
        </button>
      </div>
    </div>
  );
}

// ─── Section: Recent Activity ─────────────────────────────────────────────────

const RECENT_ACTIVITY = [
  { time: "Today 10:28 AM", text: "Installed RecovR tracker — Honda Accord A48291" },
  { time: "Today 10:14 AM", text: "Moved BMW 5 Series E51388 to Service Bay" },
  { time: "Today 9:41 AM", text: "Accepted showroom request from Sales" },
  { time: "Today 8:47 AM", text: "Replaced stock tag — Ford F-150 C84711" },
  { time: "Today 7:02 AM", text: "Logged in — Session started" },
  { time: "Yesterday 5:30 PM", text: "Logged out" },
  { time: "Yesterday 4:15 PM", text: "Completed 3 tasks" },
  { time: "Yesterday 9:00 AM", text: "Logged in" },
];

function RecentActivitySection() {
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-5">
      <p className="text-[12px] font-semibold text-slate-600 mb-4">Recent Activity</p>
      <div className="flex flex-col gap-0">
        {RECENT_ACTIVITY.map((entry, i) => (
          <div key={i} className="flex items-start gap-3 pb-4 last:pb-0 relative">
            <div className="flex flex-col items-center">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1 flex-shrink-0" />
              {i < RECENT_ACTIVITY.length - 1 && (
                <div className="w-px bg-slate-100 mt-1" style={{ minHeight: 28 }} />
              )}
            </div>
            <div>
              <p className="text-[12px] text-slate-700">{entry.text}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">{entry.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

const SECTIONS: { id: SectionId; label: string }[] = [
  { id: "profile", label: "Profile" },
  { id: "notifications", label: "Notifications" },
  { id: "appearance", label: "Appearance" },
  { id: "security", label: "Security" },
  { id: "current-session", label: "Current Session" },
  { id: "recent-activity", label: "Recent Activity" },
];

function SectionContent({ section }: { section: SectionId }) {
  switch (section) {
    case "profile": return <ProfileSection />;
    case "notifications": return <NotificationsSection />;
    case "appearance": return <AppearanceSection />;
    case "security": return <SecuritySection />;
    case "current-session": return <CurrentSessionSection />;
    case "recent-activity": return <RecentActivitySection />;
  }
}

export default function Profile(): JSX.Element {
  const [activeSection, setActiveSection] = useState<SectionId>("profile");

  return (
    <div className="h-full flex flex-col bg-slate-50 overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b border-slate-100 px-4 sm:px-6 py-4">
        <h1 className="text-[18px] font-bold text-slate-800">Profile & Settings</h1>
        <p className="text-[12px] text-slate-400 mt-0.5">Manage your account, preferences, and session</p>
      </div>

      {/* Body -- below lg the section nav becomes a horizontal wrapping tab
          row above the content instead of a fixed-width left rail (same
          "stack, don't scroll" approach used throughout this pass); lg+ is
          the original unchanged left-nav layout. */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-y-auto lg:overflow-hidden">
        {/* Left nav */}
        <div className="w-full lg:w-48 flex-shrink-0 border-b lg:border-b-0 lg:border-r border-slate-100 bg-white lg:overflow-y-auto py-2 lg:py-3 flex flex-wrap lg:block gap-1 px-2 lg:px-0">
          {SECTIONS.map((sec) => (
            <button
              key={sec.id}
              onClick={() => setActiveSection(sec.id)}
              className={`w-auto lg:w-full text-left px-3 lg:px-4 py-2 lg:py-2.5 rounded-lg lg:rounded-none text-[13px] font-medium whitespace-nowrap transition-colors ${
                activeSection === sec.id
                  ? "text-blue-700 bg-blue-50"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              {sec.label}
            </button>
          ))}
        </div>

        {/* Content -- flex-shrink-0 below lg for the same reason as
            Dashboard.tsx's left column / VehicleDetail.tsx's panel row:
            the parent's overflow-y-auto at that breakpoint expects to grow
            past the viewport, so this child must not flex-shrink below its
            content height. lg:flex-1 restores the original fill-remaining-
            width behavior once the parent is bounded and non-scrolling. */}
        <div className="flex-shrink-0 lg:flex-1 lg:overflow-y-auto p-4 sm:p-6">
          <div className="max-w-xl">
            <SectionContent section={activeSection} />
          </div>
        </div>
      </div>
    </div>
  );
}
