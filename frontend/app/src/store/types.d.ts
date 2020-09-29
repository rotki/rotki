import { BalanceState } from '@/store/balances/types';
import { Section, Status } from '@/store/const';
import { NotificationState } from '@/store/notifications/state';
import { TaxReportState } from '@/store/reports/state';
import { SessionState } from '@/store/session/types';
import { SettingsState } from '@/store/settings/types';
import { TaskState } from '@/store/tasks/state';

export interface ActionStatus {
  readonly message?: string;
  readonly success: boolean;
}

export interface StatusPayload {
  readonly status: Status;
  readonly section: Section;
}

export interface Version {
  readonly version: string;
  readonly latestVersion: string;
  readonly downloadUrl: string;
}

type SectionStatus = { [section: string]: Status };

export interface RotkehlchenState {
  message: Message;
  version: Version;
  connected: boolean;
  status: SectionStatus;
  session?: SessionState;
  tasks?: TaskState;
  notifications?: NotificationState;
  reports?: TaxReportState;
  balances?: BalanceState;
  settings?: SettingsState;
}

export interface Message {
  readonly title: string;
  readonly description: string;
  readonly success: boolean;
}
