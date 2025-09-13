import { sectionTitle, card } from "@/lib/ui";

export default function Page() {
  return (
    <section className="flex flex-col gap-6">
      <h1 className={sectionTitle}>Integrations</h1>
      <div className={card}>
        <h2 className="text-base font-medium">Data Sources</h2>
        <p className="text-sm text-zinc-400 mt-1">
          Connect your data sources to enable monitoring and analysis.
        </p>
      </div>
      <div className={card}>
        <h2 className="text-base font-medium">API Connections</h2>
        <p className="text-sm text-zinc-400 mt-1">
          Manage your API integrations and authentication tokens.
        </p>
      </div>
    </section>
  );
}
