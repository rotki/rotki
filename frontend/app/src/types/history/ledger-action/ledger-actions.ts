// Ledger Actions
import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { type PaginationRequestPayload } from '@/types/common';
import { EntryMeta } from '@/types/history/meta';
import { TradeLocation } from '@/types/history/trade/location';
import { LedgerActionEnum } from '@/types/history/ledger-action/ledger-actions-type';
import { CollectionCommonFields } from '@/types/collection';

export const LedgerAction = z.object({
  identifier: z.number(),
  timestamp: z.number(),
  actionType: LedgerActionEnum,
  location: TradeLocation,
  amount: NumericString,
  asset: z.string(),
  rate: NumericString.nullish(),
  rateAsset: z.string().nullish(),
  link: z.string().nullish(),
  notes: z.string().nullish()
});

export type LedgerAction = z.infer<typeof LedgerAction>;

export const LedgerActionCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(
    z
      .object({
        entry: LedgerAction
      })
      .merge(EntryMeta)
  )
});

export interface LedgerActionRequestPayload
  extends PaginationRequestPayload<LedgerAction> {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly location?: string;
  readonly asset?: string;
  readonly action?: string;
}

export type NewLedgerAction = Omit<LedgerAction, 'identifier'>;

export interface LedgerActionEntry extends LedgerAction, EntryMeta {}
