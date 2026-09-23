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
  BEACONCHAIN_RATE_LIMITED = 'BEACONCHAIN_RATE_LIMITED',
  DESERIALIZATION_ERROR = 'DESERIALIZATION_ERROR',
  MONERIUM_AUTH = 'MONERIUM_AUTH',
  ORACLE_PENALIZED = 'ORACLE_PENALIZED',
}

/**
 * A notification group, optionally narrowed to a single subject.
 *
 * Some groups cover a whole class of notifications that must not collapse into each other: one
 * oracle being penalized is a different event from another oracle being penalized, and both need
 * their own entry. Those append a discriminator (`ORACLE_PENALIZED:coingecko`) so the grouping
 * stays per subject.
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
  CALENDAR_REMINDER: 'calendar_reminder',
  DEFAULT: 'default',
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

interface NotificationBase {
  readonly title: string;
  readonly message: string;
  readonly severity: Severity;
  readonly category: NotificationCategory;
  readonly action?: NotificationAction | NotificationAction[];
  readonly group?: NotificationGroupKey;
  readonly groupCount?: number;
  readonly priority?: Priority;
  readonly extras?: Record<string, unknown>;
}

export interface NotificationPayload extends NotificationBase {
  /**
   * Silences a notification whose priority would otherwise pop it.
   *
   * @remarks
   * Suppression only, which is why the type is `false` rather than `boolean`. Whether a
   * notification interrupts is the dispatcher's decision, derived from `priority`, so a caller
   * cannot promote itself into a popup by asking. It can still opt out, because a condition that
   * already has a home elsewhere in the UI should not also interrupt.
   */
  readonly display?: false;
  readonly duration?: number;
}

export interface NotificationData extends NotificationBase {
  readonly id: number;
  readonly display: boolean;
  readonly duration: number;
  readonly date: Date;
  /**
   * Whether the user has opened the drawer since this arrived.
   *
   * @remarks
   * Novelty, not state. It drives the "something new is here" dot and nothing else, so an item
   * that still needs the user stays on the badge after being read: opening a drawer does not
   * resolve a missing API key.
   */
  readonly read: boolean;
}

export type Notification = SemiPartial<NotificationPayload, 'title' | 'message'>;
