import { z } from 'zod';
import { arrayify } from '@/modules/core/common/data/array';
import { CommaSeparatedStringSchema, RouterExpandedIdsSchema } from '@/modules/core/table/route';

/**
 * A repeated query key (`?chain=eth&chain=optimism`) or a comma-joined one (`?chain=eth,optimism`).
 * The param source writes the joined form, but the matcher-bound chain filter this replaced wrote
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
 * Everything the blockchain accounts table reads back out of the URL: its three filter pills plus
 * the expansion state of the table itself.
 */
export const AccountExternalFilterSchema = z.object({
  addresses: CommaSeparatedStringSchema,
  chain: MultipleStringSchema,
  q: z.string().optional(),
  tab: z.coerce.number().optional(),
  tags: CommaSeparatedStringSchema,
  ...RouterExpandedIdsSchema.shape,
});
