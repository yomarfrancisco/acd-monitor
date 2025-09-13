import { sectionTitle, card, dashboardCtaBtnClass } from "@/lib/ui";

export default function Page() {
  return (
    <section className="flex flex-col gap-6">
      <h1 className={sectionTitle}>Overview</h1>

      <div className={card}>
        <h2 className="text-base font-medium">Pro Plan</h2>
        <p className="text-sm text-zinc-400 mt-1">
          Unlimited tab completions, extended Agent limits, and access to most features.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <button className={dashboardCtaBtnClass}>Manage Subscription</button>
          <button className={dashboardCtaBtnClass}>Edit Limit</button>
        </div>
      </div>

      <div className={card}>
        <h2 className="text-base font-medium">Your Analytics</h2>
        <div className="mt-4 h-64 rounded-lg bg-white/5">
          {/* Chart mounts here; ensure chart component observes parent width */}
        </div>
        <p className="mt-3 text-center text-sm text-zinc-400">No Analytics Available Yet</p>
      </div>
    </section>
  );
}
