import { sectionTitle, card } from "@/lib/ui";

export default function Page() {
  return (
    <section className="flex flex-col gap-6">
      <h1 className={sectionTitle}>Billing & Invoices</h1>
      <div className={card}>
        <h2 className="text-base font-medium">Current Plan</h2>
        <p className="text-sm text-zinc-400 mt-1">
          Manage your subscription and billing information.
        </p>
      </div>
    </section>
  );
}
