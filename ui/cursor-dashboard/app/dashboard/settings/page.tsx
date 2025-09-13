import { sectionTitle, card } from "@/lib/ui";

export default function Page() {
  return (
    <section className="flex flex-col gap-6">
      <h1 className={sectionTitle}>Settings</h1>
      <div className={card}>
        <p className="text-sm text-zinc-400">Settings placeholder.</p>
      </div>
    </section>
  );
}
