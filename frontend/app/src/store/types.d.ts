import { BalanceState } from '@/store/balances/types';
import { Section, Status } from '@/store/const';
import { DefiState } from '@/store/defi/types';
import { SessionState } from '@/store/session/types';
import { SettingsState } from '@/store/settings/state';
import { StatisticsState } from '@/store/statistics/types';

type ActionFailure = {
  readonly message: string;
  readonly success: false;
};

type ActionSuccess = {
  readonly success: true;
};

export type ActionStatus = ActionFailure | ActionSuccess;

export type SuccessMessage = {
  readonly success: boolean;
  readonly message: string;
};

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
  status: SectionStatus;
  session?: SessionState;
  balances?: BalanceState;
  settings?: SettingsState;
  defi?: DefiState;
  statistics?: StatisticsState;
}

export type ActionDataEntry = {
  readonly identifier: string;
  readonly label: string;
  readonly icon?: string | undefined;
  readonly image?: string | undefined;
  readonly color?: string | undefined;
  readonly matcher?: (identifier: string) => boolean | undefined;
};
