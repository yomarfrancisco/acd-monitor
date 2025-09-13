import { sectionTitle, card } from "@/lib/ui";

export default function Page() {
  return (
    <section className="flex flex-col gap-6">
      <h1 className={sectionTitle}>Overview</h1>
      <div className={card}>
        <p className="text-sm text-zinc-400">Overview placeholder.</p>
      </div>
    </section>
  );
}
