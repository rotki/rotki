import type { Awaitable, SemiPartial } from '../utils';

export enum Severity {
  WARNING = 'warning',
  ERROR = 'error',
  INFO = 'info',
}

/**
 * What a notification is, which decides whether it interrupts and where the drawer files it.
 *
 * @remarks
 * A condition, something that stays true until the user resolves it, is never a notification:
 * it is raised in the action center instead.
 */
export const NotificationKind = {
  /** News with an action: new tokens detected, premium turned active. Pops. */
  ANNOUNCEMENT: 'announcement',
  /** A classified backend error or warning. Recorded, never pops. */
  BACKEND_PROBLEM: 'backend_problem',
  /** A background request that failed with nowhere else to show it. Recorded, never pops. */
  FAILURE: 'failure',
  /** A calendar reminder, acknowledged by its action. Pops. */
  REMINDER: 'reminder',
  /** The outcome of something the user started that has no other surface. Pops. */
  RESULT: 'result',
} as const;

export type NotificationKind = (typeof NotificationKind)[keyof typeof NotificationKind];

export enum NotificationGroup {
  NEW_DETECTED_TOKENS = 'NEW_DETECTED_TOKENS',
  BEACONCHAIN_RATE_LIMITED = 'BEACONCHAIN_RATE_LIMITED',
  MONERIUM_AUTH = 'MONERIUM_AUTH',
  USER_MESSAGE = 'USER_MESSAGE',
  ASSET_MAPPINGS = 'ASSET_MAPPINGS',
}

/**
 * A notification group, optionally narrowed to a single subject.
 *
 * Some groups cover a whole class of notifications that must not collapse into each other: one
 * backend problem is a different event from another, and both need their own entry. Those append
 * a discriminator (`USER_MESSAGE:<identity>`) so the grouping stays per subject.
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
  readonly kind: NotificationKind;
  readonly action?: NotificationAction | NotificationAction[];
  readonly group?: NotificationGroupKey;
  readonly groupCount?: number;
  readonly extras?: Record<string, unknown>;
}

export interface NotificationPayload extends NotificationBase {
  /**
   * Silences a notification whose kind would otherwise pop it.
   *
   * @remarks
   * Suppression only, which is why the type is `false` rather than `boolean`. Whether a
   * notification interrupts is the dispatcher's decision, derived from `kind`, so a caller
   * cannot promote itself into a popup by asking. It can still opt out, because a condition that
   * already has a home elsewhere in the UI should not also interrupt.
   */
  readonly display?: false;
  readonly duration?: number;
  /** When it happened, for a notification about something that happened before it arrived. */
  readonly date?: Date;
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

/**
 * What a caller hands the dispatcher.
 *
 * @remarks
 * `severity` and `kind` are required: a failure posted without a severity used to fall back to
 * INFO and was filed as news, so the caller has to say what it is reporting and what it is.
 */
export type Notification = SemiPartial<NotificationPayload, 'title' | 'message' | 'severity' | 'kind'>;
