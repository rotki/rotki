import { type SemiPartial } from '../index';

export enum Severity {
  WARNING = 'warning',
  ERROR = 'error',
  INFO = 'info'
}

export interface Message {
  readonly title: string;
  readonly description: string;
  readonly success: boolean;
}

interface NotificationBase {
  readonly title: string;
  readonly message: string;
  readonly severity: Severity;
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
