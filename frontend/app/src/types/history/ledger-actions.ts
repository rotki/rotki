// Ledger Actions
import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { getCollectionResponseType } from '@/types/collection';
import { PaginationRequestPayload } from '@/types/common';
import { getEntryWithMeta } from '@/types/history/meta';
import { TradeLocation } from '@/types/history/trade-location';
import { LedgerActionEnum } from '@/types/ledger-actions';

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
export const LedgerActionCollectionResponse = getCollectionResponseType(
  getEntryWithMeta(LedgerAction)
);
export interface LedgerActionRequestPayload
  extends PaginationRequestPayload<LedgerAction> {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly location?: string;
  readonly asset?: string;
  readonly action?: string;
}

export type NewLedgerAction = Omit<LedgerAction, 'identifier'>;
