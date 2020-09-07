import { BigNumber } from 'bignumber.js';

export interface ApiSupportedAsset {
  readonly active?: boolean;
  readonly ended?: number;
  readonly name: string;
  readonly started?: number;
  readonly symbol: string;
  readonly type: string;
}

export interface SupportedAssets {
  readonly [key: string]: ApiSupportedAsset;
}

export interface LimitedResponse<T> {
  readonly entries: T;
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
