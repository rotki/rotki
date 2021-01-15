import { BigNumber } from 'bignumber.js';
import { IgnoreActionType } from '@/store/history/types';

export const SYNC_UPLOAD = 'upload';
export const SYNC_DOWNLOAD = 'download';

const SYNC_ACTIONS = [SYNC_DOWNLOAD, SYNC_UPLOAD] as const;

export type SyncAction = typeof SYNC_ACTIONS[number];

interface ApiSupportedAsset {
  readonly active?: boolean;
  readonly ended?: number;
  readonly name: string;
  readonly started?: number;
  readonly symbol: string;
  readonly type: string;
  readonly ethereumAddress?: string;
}

export interface SupportedAssets {
  readonly [key: string]: ApiSupportedAsset;
}

export interface EntryWithMeta<T> {
  readonly entry: T;
  readonly ignoredInAccounting: boolean;
}

export interface LimitedResponse<T> {
  readonly entries: T[];
  readonly entriesFound: number;
  readonly entriesLimit: number;
}

export class TaskNotFoundError extends Error {}

export interface ActionResult<T> {
  readonly result: T;
  readonly message: string;
}

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

export interface Balance {
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
}

export interface HasBalance {
  readonly balance: Balance;
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
  readonly historyProcessStartTs: number;
  readonly historyProcessCurrentTs: number;
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

export interface VersionCheck {
  readonly our_version?: string;
  readonly latest_version?: string;
  readonly download_url?: string;
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

export type IgnoreActionResult = {
  readonly [key in IgnoreActionType]?: string[];
};
