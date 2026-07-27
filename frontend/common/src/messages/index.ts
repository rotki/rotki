import type { Awaitable, SemiPartial } from '../utils';

export enum Severity {
  WARNING = 'warning',
  ERROR = 'error',
  INFO = 'info',
  REMINDER = 'reminder',
}

export enum Priority {
  BULK,
  NORMAL,
  HIGH,
  ACTION,
}

export enum NotificationGroup {
  NEW_DETECTED_TOKENS = 'NEW_DETECTED_TOKENS',
  ASSET_SEARCH_ERROR = 'ASSET_SEARCH_ERROR',
  BEACONCHAIN_RATE_LIMITED = 'BEACONCHAIN_RATE_LIMITED',
  DESERIALIZATION_ERROR = 'DESERIALIZATION_ERROR',
  HISTORICAL_BALANCES = 'HISTORICAL_BALANCES',
  MISSING_EXCHANGE_MAPPING = 'MISSING_EXCHANGE_MAPPING',
  GNOSIS_PAY_SESSION_EXPIRED = 'GNOSIS_PAY_SESSION_EXPIRED',
  INTERNAL_TX_CONFLICT_RESOLUTION = 'INTERNAL_TX_CONFLICT_RESOLUTION',
  MISSING_API_KEY = 'MISSING_API_KEY',
  NO_AVAILABLE_INDEXERS = 'NO_AVAILABLE_INDEXERS',
  UNMATCHED_ASSET_MOVEMENTS = 'UNMATCHED_ASSET_MOVEMENTS',
  UNMATCHED_BRIDGE_TRANSACTIONS = 'UNMATCHED_BRIDGE_TRANSACTIONS',
}

/**
 * A notification group, optionally narrowed to a single subject.
 *
 * Some groups cover a whole class of notifications that must not collapse into each other: one
 * chain missing its indexers is a different problem from another chain missing its indexers, and
 * both need their own entry with their own actions. Those append a discriminator
 * (`NO_AVAILABLE_INDEXERS:binance_sc`) so the grouping stays per subject.
 */
export type NotificationGroupKey = NotificationGroup | `${NotificationGroup}:${string}`;

/**
 * The group a key belongs to, discarding any discriminator. Grouping policy (cooldowns, display
 * schedules) is defined per group, while collapsing happens per key. Returns undefined for a key
 * that names no known group, letting callers fall back to their default policy.
 */
export function notificationGroupOf(key: string): NotificationGroup | undefined {
  const separator = key.indexOf(':');
  const group = separator === -1 ? key : key.slice(0, separator);
  return Object.values(NotificationGroup).find(value => value === group);
}

export const NotificationCategory = {
  ADDRESS_MIGRATION: 'address_migration',
  BEACONCHAIN: 'beaconchain',
  BLOCKSCOUT: 'blockscout',
  CALENDAR_REMINDER: 'calendar_reminder',
  DEFAULT: 'default',
  ETHERSCAN: 'etherscan',
  HELIUS: 'helius',
  THEGRAPH: 'thegraph',
} as const;

export type NotificationCategory = (typeof NotificationCategory)[keyof typeof NotificationCategory];

export interface Message {
  readonly title: string;
  readonly description: string;
  readonly success: boolean;
}

export interface NotificationAction {
  readonly label: string;
  readonly action: Awaitable;
  readonly icon?: string;
  readonly persist?: boolean;
  readonly danger?: boolean;
}

export interface I18nParam {
  message: string;
  choice: number;
  props: Record<string, string>;
}

interface NotificationBase {
  readonly title: string;
  readonly message: string;
  readonly severity: Severity;
  readonly category: NotificationCategory;
  readonly action?: NotificationAction | NotificationAction[];
  readonly group?: NotificationGroupKey;
  readonly groupCount?: number;
  readonly i18nParam?: I18nParam;
  readonly priority?: Priority;
  readonly extras?: Record<string, unknown>;
}

export interface NotificationPayload extends NotificationBase {
  readonly display?: boolean;
  readonly duration?: number;
}

export interface NotificationData extends NotificationBase {
  readonly id: number;
  readonly display: boolean;
  readonly duration: number;
  readonly date: Date;
}

export type Notification = SemiPartial<NotificationPayload, 'title' | 'message'>;
