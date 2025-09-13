import { sectionTitle, card } from "@/lib/ui";

export default function Page() {
  return (
    <section className="flex flex-col gap-6">
      <h1 className={sectionTitle}>Contact Us</h1>
      <div className={card}>
        <h2 className="text-base font-medium">Support</h2>
        <p className="text-sm text-zinc-400 mt-1">
          Get help with your account, billing, or technical issues.
        </p>
      </div>
    </section>
  );
}
