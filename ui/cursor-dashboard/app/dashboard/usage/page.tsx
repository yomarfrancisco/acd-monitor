import { sectionTitle, card } from "@/lib/ui";

export default function Page() {
  return (
    <section className="flex flex-col gap-6">
      <h1 className={sectionTitle}>Usage</h1>
      <div className={card}>
        <h2 className="text-base font-medium">Current Usage</h2>
        <p className="text-sm text-zinc-400 mt-1">
          View your current usage statistics and limits.
        </p>
      </div>
    </section>
  );
}
