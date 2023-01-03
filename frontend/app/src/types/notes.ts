import { NumericString } from '@rotki/common';
import { z } from 'zod';

export const UserNote = z.object({
  identifier: z.number(),
  title: z.string(),
  content: z.string(),
  location: z.string(),
  lastUpdateTimestamp: z.number(),
  isPinned: z.boolean()
});

export type UserNote = z.infer<typeof UserNote>;

export const UserNotes = z.array(UserNote);

export type UserNotes = z.infer<typeof UserNotes>;

export const UserNoteCollectionResponse = z.object({
  entries: z.array(UserNote),
  entriesFound: z.number(),
  entriesLimit: z.number().default(-1),
  entriesTotal: z.number(),
  totalUsdValue: NumericString.nullish()
});

export interface UserNotesFilter {
  titleSubstring: string;
  limit: number;
  offset: number;
  location: string;
  orderByAttributes: string[];
  ascending: boolean[];
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
  HISTORY_TRANSACTIONS = 'HISTORY_TRANSACTIONS',
  HISTORY_LEDGER_ACTIONS = 'HISTORY_LEDGER_ACTIONS',
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
  LOCATIONS = 'LOCATIONS'
}
