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
