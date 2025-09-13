import { sectionTitle, card } from "@/lib/ui";

export default function Page() {
  return (
    <section className="flex flex-col gap-6">
      <h1 className={sectionTitle}>Background Agents</h1>
      <div className={card}>
        <h2 className="text-base font-medium">Agent Configuration</h2>
        <p className="text-sm text-zinc-400 mt-1">
          Configure your background agents for automated monitoring and analysis.
        </p>
      </div>
      <div className={card}>
        <h2 className="text-base font-medium">Default Settings</h2>
        <p className="text-sm text-zinc-400 mt-1">
          Set default parameters and behavior for your background agents.
        </p>
      </div>
    </section>
  );
}
