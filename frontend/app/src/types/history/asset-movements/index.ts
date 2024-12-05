// Asset Movements
import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { EntryMeta } from '@/types/history/meta';
import { CollectionCommonFields } from '@/types/collection';
import type { PaginationRequestPayload } from '@/types/common';

export const MovementCategory = z.enum(['deposit', 'withdrawal']);

export type MovementCategory = z.infer<typeof MovementCategory>;

export const AssetMovement = z.object({
  address: z.string().nullable(),
  amount: NumericString,
  asset: z.string(),
  category: MovementCategory,
  fee: NumericString,
  feeAsset: z.string(),
  identifier: z.string(),
  link: z.string(),
  location: z.string(),
  timestamp: z.number(),
  transactionId: z.string().nullable(),
});

export type AssetMovement = z.infer<typeof AssetMovement>;

export const AssetMovementCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(
    z
      .object({
        entry: AssetMovement,
      })
      .merge(EntryMeta),
  ),
});

export interface AssetMovementRequestPayload extends PaginationRequestPayload<AssetMovement> {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly location?: string;
  readonly asset?: string;
  readonly action?: string;
  readonly excludeIgnoredAssets?: boolean;
}

export interface AssetMovementEntry extends AssetMovement, EntryMeta {}
