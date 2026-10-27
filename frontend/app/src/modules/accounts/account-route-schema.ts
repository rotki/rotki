import { z } from 'zod';
import { arrayify } from '@/modules/core/common/data/array';
import { CommaSeparatedStringSchema } from '@/modules/core/table/route';

/**
 * A repeated query key (`?chain=eth&chain=optimism`) or a comma-joined one (`?chain=eth,optimism`).
 * The param source writes the joined form, but the filter-bound chain filter this replaced wrote
 * the repeated one, so a link from before it moved still parses rather than throwing here and
 * taking the whole route update with it.
 */
const MultipleStringSchema = z
  .array(z.string())
  .or(z.string())
  .transform(value => arrayify(value).flatMap(entry => entry.split(',')))
  .optional()
  .transform(value => value ?? []);

/**
 * Everything the blockchain accounts table reads back out of the URL: its three filter pills. The
 * details drawer keeps its own keys (`use-account-details-route.ts`).
 */
export const AccountExternalFilterSchema = z.object({
  addresses: CommaSeparatedStringSchema,
  chain: MultipleStringSchema,
  tags: CommaSeparatedStringSchema,
});
