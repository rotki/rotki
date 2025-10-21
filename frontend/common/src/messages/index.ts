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
  DESERIALIZATION_ERROR = 'DESERIALIZATION_ERROR',
  MISSING_EXCHANGE_MAPPING = 'MISSING_EXCHANGE_MAPPING',
  GNOSIS_PAY_SESSION_EXPIRED = 'GNOSIS_PAY_SESSION_EXPIRED',
}

export const NotificationCategory = {
  ADDRESS_MIGRATION: 'address_migration',
  BEACONCHAIN: 'beaconchain',
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
  readonly group?: NotificationGroup;
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
