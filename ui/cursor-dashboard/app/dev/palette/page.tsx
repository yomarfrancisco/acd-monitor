export default function Palette() {
  const Tile = ({label, cls}:{label:string; cls:string}) => (
    <div className={`rounded-xl p-6 ${cls} text-[#f9fafb] border border-[#2a2a2a]`}>{label}</div>
  );
  return (
    <div className="min-h-screen bg-[#0f0f10] p-8 grid gap-6 md:grid-cols-3">
      <Tile label="bg-bg-tile (#1a1a1a)" cls="bg-bg-tile" />
      <Tile label="bg-bg-tile2 (#1e1e1e)" cls="bg-bg-tile2" />
      <Tile label="bg-bg-surface (#212121)" cls="bg-bg-surface" />
    </div>
  );
}
