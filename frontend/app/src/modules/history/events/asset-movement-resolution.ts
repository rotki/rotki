import { z } from 'zod';

/**
 * How an unmatched asset movement was resolved, stamped by the backend on the event it rewrote.
 *
 * @remarks
 * The same `matchedAssetMovement` key also carries ordinary match metadata (the counterpart's group
 * and exchange), which shares none of these fields - hence a resolution is recognised by
 * `resolution`, not by the key's presence.
 */
export const MatchedAssetMovementResolution = z.object({
  direction: z.enum(['deposit', 'withdrawal']).nullish(),
  resolution: z.literal('external').nullish(),
});
