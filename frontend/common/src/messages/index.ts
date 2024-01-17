import type { SemiPartial } from '../index';

export enum Severity {
  WARNING = 'warning',
  ERROR = 'error',
  INFO = 'info',
}

export enum Priority {
  BULK,
  NORMAL,
  HIGH,
  ACTION,
}

export enum NotificationGroup {
  NEW_DETECTED_TOKENS = 'NEW_DETECTED_TOKENS',
  DB_UPLOAD_RESULT = 'DB_UPLOAD_RESULT',
}

export const NotificationCategory = {
  DEFAULT: 'default',
  ADDRESS_MIGRATION: 'address_migration',
} as const;

export type NotificationCategory =
  (typeof NotificationCategory)[keyof typeof NotificationCategory];

export interface Message {
  readonly title: string;
  readonly description: string;
  readonly success: boolean;
}

export interface NotificationAction {
  readonly label: string;
  readonly action: () => void;
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

export type Notification = SemiPartial<
  NotificationPayload,
  'title' | 'message'
>;
