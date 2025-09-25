export type EnvEvent = {
  id: string;
  ts: number;         // ms since epoch
  label: string;      // short tag to display
  color: string;      // hex
};

export function defaultEnvEvents(): EnvEvent[] {
  return [
    { id: "env-1", ts: Date.parse("2025-02-01T00:00:00Z"), label: "Regime A→B", color: "#ef4444" }, // red
    { id: "env-2", ts: Date.parse("2025-06-01T00:00:00Z"), label: "Policy Shift", color: "#f59e0b" }, // amber
    { id: "env-3", ts: Date.parse("2025-07-01T00:00:00Z"), label: "Liquidity ↑", color: "#10b981" }, // green
  ];
}
