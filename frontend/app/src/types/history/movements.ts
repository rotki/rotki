// Asset Movements
import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { type PaginationRequestPayload } from '@/types/common';
import { EntryMeta } from '@/types/history/meta';
import { TradeLocation } from '@/types/history/trade-location';

export const MovementCategory = z.enum(['deposit', 'withdrawal']);
export type MovementCategory = z.infer<typeof MovementCategory>;
export const AssetMovement = z.object({
  identifier: z.string(),
  location: TradeLocation,
  category: MovementCategory,
  address: z.string().nullable(),
  transactionId: z.string().nullable(),
  timestamp: z.number(),
  asset: z.string(),
  amount: NumericString,
  feeAsset: z.string(),
  fee: NumericString,
  link: z.string()
});
export type AssetMovement = z.infer<typeof AssetMovement>;
export const AssetMovementCollectionResponse = z.object({
  entries: z.array(
    z
      .object({
        entry: AssetMovement
      })
      .merge(EntryMeta)
  ),
  entriesFound: z.number(),
  entriesLimit: z.number().default(-1),
  entriesTotal: z.number(),
  totalUsdValue: NumericString.nullish()
});
export interface AssetMovementRequestPayload
  extends PaginationRequestPayload<AssetMovement> {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly location?: string;
  readonly asset?: string;
  readonly action?: string;
}
