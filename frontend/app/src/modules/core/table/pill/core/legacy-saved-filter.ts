import { AssetInfoWithId } from '@rotki/common';
import { z } from 'zod';

/**
 * One value of a filter saved by the bar that came before the pills, as it sits in the
 * `savedFilters` setting: one entry per value, keyed by the field it belongs to, with exclusion as
 * a flag beside it. An asset was stored as its whole info object rather than its identifier.
 *
 * Read-only, and deliberately the whole of what is left of that model: the bar it belonged to is
 * gone, so nothing needs its behaviour — only enough shape to move a stored filter into a saved
 * view (`use-saved-views.ts`). It is one file so that dropping the conversion later is one
 * deletion.
 */
export const LegacySavedFilterEntry = z.object({
  exclude: z.boolean().optional(),
  key: z.string(),
  value: AssetInfoWithId.or(z.string()).or(z.boolean()),
});

export type LegacySavedFilterEntry = z.infer<typeof LegacySavedFilterEntry>;

/** One location's saved filters: a list of filters, each a list of the values it holds. */
export const LegacySavedFilters = z.array(z.array(LegacySavedFilterEntry));
