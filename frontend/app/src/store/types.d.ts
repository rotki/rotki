import { AssetState } from '@/store/assets/types';
import { BalanceState } from '@/store/balances/types';
import { Section, Status } from '@/store/const';
import { DefiState } from '@/store/defi/types';
import { SessionState } from '@/store/session/types';
import { SettingsState } from '@/store/settings/state';
import { StatisticsState } from '@/store/statistics/types';

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
  status: SectionStatus;
  session?: SessionState;
  balances?: BalanceState;
  settings?: SettingsState;
  defi?: DefiState;
  statistics?: StatisticsState;
  assets?: AssetState;
}
