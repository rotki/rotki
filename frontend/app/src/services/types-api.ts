import { SupportedAsset } from '@rotki/common/lib/data';
import { AxiosInstance, AxiosResponseTransformer } from 'axios';

export const SYNC_UPLOAD = 'upload';
export const SYNC_DOWNLOAD = 'download';

const SYNC_ACTIONS = [SYNC_DOWNLOAD, SYNC_UPLOAD] as const;

export type SyncAction = typeof SYNC_ACTIONS[number];

export interface SupportedAssets {
  readonly [key: string]: Omit<SupportedAsset, 'identifier'>;
}

export class TaskNotFoundError extends Error {}

export interface AsyncQuery {
  readonly task_id: number;
}

export interface PendingTask {
  readonly taskId: number;
}

export interface Messages {
  readonly warnings: string[];
  readonly errors: string[];
}

export interface LocationData {
  readonly time: number;
  readonly location: string;
  readonly usd_value: string;
}

// This is equivalent to python's AssetBalance named tuple
export interface DBAssetBalance {
  readonly time: number;
  readonly asset: string;
  readonly amount: string;
  readonly usd_value: string;
}

export interface PeriodicClientQueryResult {
  readonly lastBalanceSave: number;
  readonly ethNodeConnection: boolean;
  readonly lastDataUploadTs: number;
}

export interface NetValue {
  readonly times: number[];
  readonly data: number[];
}

export interface SingleAssetBalance {
  readonly time: number;
  readonly amount: string;
  readonly usd_value: string;
}

export interface BackendVersion {
  readonly ourVersion?: string;
  readonly latestVersion?: string;
  readonly downloadUrl?: string;
}

export interface BackendInfo {
  readonly version: BackendVersion;
  readonly dataDirectory: string;
}

export interface GeneralAccountData {
  readonly address: string;
  readonly label: string | null;
  readonly tags: string[] | null;
}

export interface XpubAccountData {
  readonly xpub: string;
  readonly derivationPath: string | null;
  readonly label: string | null;
  readonly tags: string[] | null;
  readonly addresses: GeneralAccountData[] | null;
}

export interface BtcAccountData {
  readonly standalone: GeneralAccountData[];
  readonly xpubs: XpubAccountData[];
}

export interface TaskStatus {
  readonly pending: number[];
  readonly completed: number[];
}

export interface ApiImplementation {
  readonly axios: AxiosInstance;
  readonly baseTransformer: AxiosResponseTransformer[];
}
