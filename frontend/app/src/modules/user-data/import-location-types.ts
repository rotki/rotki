import { z } from 'zod';

const ImportLocationResolutionSchema = z.object({
  value: z.string(),
  status: z.enum(['resolved', 'ambiguous', 'unresolved']),
  location: z.string().nullable(),
  candidates: z.array(z.string()),
});

export type ImportLocationResolution = z.infer<typeof ImportLocationResolutionSchema>;

export const ImportLocationPreflightSchema = z.object({
  locations: z.array(ImportLocationResolutionSchema),
});
