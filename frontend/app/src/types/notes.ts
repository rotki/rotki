import { z } from 'zod';
import { CollectionCommonFields } from '@/types/collection';
import type { PaginationRequestPayload } from '@/types/common';

export const UserNote = z.object({
  identifier: z.number(),
  title: z.string(),
  content: z.string(),
  location: z.string(),
  lastUpdateTimestamp: z.number(),
  isPinned: z.boolean(),
});

export type UserNote = z.infer<typeof UserNote>;

export const UserNoteCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(UserNote),
});

export interface UserNotesRequestPayload extends PaginationRequestPayload<UserNote> {
  titleSubstring: string;
  location: string;
}

export enum NoteLocation {
  DASHBOARD = 'DASHBOARD',
  ACCOUNTS_BALANCES_BLOCKCHAIN = 'ACCOUNTS_BALANCES_BLOCKCHAIN',
  ACCOUNTS_BALANCES_EXCHANGE = 'ACCOUNTS_BALANCES_EXCHANGE',
  ACCOUNTS_BALANCES_NON_FUNGIBLE = 'ACCOUNTS_BALANCES_NON_FUNGIBLE',
  ACCOUNTS_BALANCES_MANUAL = 'ACCOUNTS_BALANCES_MANUAL',
  NFTS = 'NFTS',
  HISTORY_TRADES = 'HISTORY_TRADES',
  HISTORY_DEPOSITS_WITHDRAWALS = 'HISTORY_DEPOSITS_WITHDRAWALS',
  HISTORY_EVENTS = 'HISTORY_TRANSACTIONS',
  DEFI = 'DEFI',
  STATISTICS = 'STATISTICS',
  STAKING = 'STAKING',
  PROFIT_LOSS_REPORTS = 'PROFIT_LOSS_REPORTS',
  ASSETS = 'ASSETS',
  PRICE_MANAGER = 'PRICE_MANAGER',
  ADDRESS_BOOK_MANAGER = 'ETH_ADDRESS_BOOK_MANAGER',
  API_KEYS = 'API_KEYS',
  IMPORT = 'IMPORT',
  SETTINGS_GENERAL = 'SETTINGS_GENERAL',
  SETTINGS_ACCOUNTING = 'SETTINGS_ACCOUNTING',
  SETTINGS_DATA_SECURITY = 'SETTINGS_DATA_SECURITY',
  SETTINGS_MODULES = 'SETTINGS_MODULES',
  LOCATIONS = 'LOCATIONS',
  CALENDAR = 'CALENDAR',
}
