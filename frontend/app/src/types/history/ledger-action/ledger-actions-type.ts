import { z } from 'zod';

export enum LedgerActionType {
  ACTION_INCOME = 'income',
  ACTION_LOSS = 'loss',
  ACTION_DONATION = 'donation received',
  ACTION_EXPENSE = 'expense',
  ACTION_DIVIDENDS = 'dividends income',
  ACTION_AIRDROP = 'airdrop',
  ACTION_GIFT = 'gift',
  ACTION_GRANT = 'grant'
}

export const LedgerActionEnum = z.nativeEnum(LedgerActionType);

export type LedgerActionEnum = z.infer<typeof LedgerActionEnum>;
