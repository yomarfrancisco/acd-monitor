import { sectionTitle, card } from "@/lib/ui";

export default function Page() {
  return (
    <section className="flex flex-col gap-6">
      <h1 className={sectionTitle}>Documentation</h1>
      <div className={card}>
        <h2 className="text-base font-medium">Getting Started</h2>
        <p className="text-sm text-zinc-400 mt-1">
          Learn how to use the dashboard and configure your monitoring setup.
        </p>
      </div>
    </section>
  );
}
