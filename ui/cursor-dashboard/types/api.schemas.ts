import { z } from 'zod';

export const RiskSummarySchema = z.object({
  score: z.number().min(0).max(100),
  band: z.enum(['LOW','AMBER','RED']),
  confidence: z.number().min(0).max(100),
  updatedAt: z.string().datetime(),
  timeframe: z.enum(['30d','6m','1y','ytd']),
  source: z.object({
    name: z.string(),
    freshnessSec: z.number().min(0),
    quality: z.number().min(0).max(1),
  }),
});

export type RiskSummary = z.infer<typeof RiskSummarySchema>;
