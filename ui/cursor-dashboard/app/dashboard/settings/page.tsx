import { sectionTitle, card } from "@/lib/ui";

export default function Page() {
  return (
    <section className="flex flex-col gap-6">
      <h1 className={sectionTitle}>Settings</h1>
      <div className={card}>
        <h2 className="text-base font-medium">General Settings</h2>
        <p className="text-sm text-zinc-400 mt-1">
          Configure your dashboard preferences and account settings.
        </p>
      </div>
      <div className={card}>
        <h2 className="text-base font-medium">Notifications</h2>
        <p className="text-sm text-zinc-400 mt-1">
          Manage your notification preferences for alerts and updates.
        </p>
      </div>
    </section>
  );
}
