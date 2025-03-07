import type { PaginationRequestPayload } from '@/types/common';
import { CollectionCommonFields } from '@/types/collection';
import { z } from 'zod';

export const UserNote = z.object({
  content: z.string(),
  identifier: z.number(),
  isPinned: z.boolean(),
  lastUpdateTimestamp: z.number(),
  location: z.string(),
  title: z.string(),
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
  ACCOUNTS_EVM = 'ACCOUNTS_EVM',
  ACCOUNTS_BITCOIN = 'ACCOUNTS_BITCOIN',
  ACCOUNTS_SUBSTRATE = 'ACCOUNTS_SUBSTRATE',
  BALANCES_BLOCKCHAIN = 'ACCOUNTS_BALANCES_BLOCKCHAIN',
  BALANCES_EXCHANGE = 'ACCOUNTS_BALANCES_EXCHANGE',
  BALANCES_NON_FUNGIBLE = 'ACCOUNTS_BALANCES_NON_FUNGIBLE',
  BALANCES_MANUAL = 'ACCOUNTS_BALANCES_MANUAL',
  NFTS = 'NFTS',
  HISTORY_TRADES = 'HISTORY_TRADES',
  HISTORY_EVENTS = 'HISTORY_TRANSACTIONS',
  DEFI = 'DEFI',
  STATISTICS = 'STATISTICS',
  STATISTICS_HISTORY_EVENTS = 'STATISTICS_HISTORY_EVENTS',
  STAKING = 'STAKING',
  PROFIT_LOSS_REPORTS = 'PROFIT_LOSS_REPORTS',
  ASSETS = 'ASSETS',
  PRICE_MANAGER = 'PRICE_MANAGER',
  ADDRESS_BOOK_MANAGER = 'ETH_ADDRESS_BOOK_MANAGER',
  API_KEYS = 'API_KEYS',
  IMPORT = 'IMPORT',
  SETTINGS_ACCOUNT = 'SETTINGS_ACCOUNT',
  SETTINGS_GENERAL = 'SETTINGS_GENERAL',
  SETTINGS_DATABASE = 'SETTINGS_DATA_SECURITY',
  SETTINGS_ACCOUNTING = 'SETTINGS_ACCOUNTING',
  SETTINGS_ORACLE = 'SETTINGS_ORACLE',
  SETTINGS_RPC = 'SETTINGS_RPC',
  SETTINGS_MODULES = 'SETTINGS_MODULES',
  SETTINGS_INTERFACE = 'SETTINGS_INTERFACE',
  LOCATIONS = 'LOCATIONS',
  CALENDAR = 'CALENDAR',
  TAG_MANAGER = 'TAG_MANAGER',
}
