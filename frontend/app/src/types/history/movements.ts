// Asset Movements
import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { getCollectionResponseType } from '@/types/collection';
import { HistoryRequestPayload } from '@/types/history/index';
import { getEntryWithMeta } from '@/types/history/meta';
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
export const AssetMovementCollectionResponse = getCollectionResponseType(
  getEntryWithMeta(AssetMovement)
);
export type AssetMovementRequestPayload = {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly location?: string;
  readonly asset?: string;
  readonly action?: string;
} & HistoryRequestPayload<AssetMovement>;
