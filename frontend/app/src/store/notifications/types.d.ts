import { Severity } from '@/store/notifications/consts';

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
