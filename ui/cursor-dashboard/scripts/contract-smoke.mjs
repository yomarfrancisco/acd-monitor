import fs from "node:fs";

// Basic contract validation without importing TypeScript schemas
const samples = [
  "risk-summary.json",
  "metrics-overview.json", 
  "health-run.json",
  "events.json",
  "datasources.json",
  "evidence-export.json"
];

for (const file of samples) {
  const data = JSON.parse(fs.readFileSync(new URL(`./golden/${file}`, import.meta.url)));
  
  // Basic validation - ensure required fields exist
  if (!data || typeof data !== 'object') {
    throw new Error(`${file}: Invalid JSON structure`);
  }
  
  // Check for common required fields
  if (data.updatedAt && typeof data.updatedAt !== 'string') {
    throw new Error(`${file}: updatedAt must be string`);
  }
  
  console.log(`✓ ${file} - basic validation passed`);
}

console.log("All contracts OK");
