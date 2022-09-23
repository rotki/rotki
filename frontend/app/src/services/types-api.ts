import { SupportedAsset } from '@rotki/common/lib/data';
import { AxiosInstance, AxiosResponseTransformer } from 'axios';
import { z } from 'zod';
import { ActiveLogLevel } from '@/electron-main/ipc';
import { getCollectionResponseType } from '@/types/collection';

export const SYNC_UPLOAD = 'upload';
export const SYNC_DOWNLOAD = 'download';

const SYNC_ACTIONS = [SYNC_DOWNLOAD, SYNC_UPLOAD] as const;

export type SyncAction = typeof SYNC_ACTIONS[number];

export const SupportedAssets = getCollectionResponseType(SupportedAsset);

export type SupportedAssets = z.infer<typeof SupportedAssets>;

export class TaskNotFoundError extends Error {}

export interface PendingTask {
  readonly taskId: number;
}

const BackendVersion = z.object({
  ourVersion: z.string().optional(),
  latestVersion: z.string().nullish(),
  downloadUrl: z.string().nullish()
});

export const BackendInfo = z.object({
  logLevel: ActiveLogLevel,
  version: BackendVersion,
  dataDirectory: z.string()
});

export type BackendInfo = z.infer<typeof BackendInfo>;

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

const NumericBackendArgument = z.object({
  value: z.number().nonnegative(),
  isDefault: z.boolean()
});

export type NumericBackendArgument = z.infer<typeof NumericBackendArgument>;

export const BackendConfiguration = z.object({
  maxSizeInMbAllLogs: NumericBackendArgument,
  maxLogfilesNum: NumericBackendArgument,
  sqliteInstructions: NumericBackendArgument
});

export type BackendConfiguration = z.infer<typeof BackendConfiguration>;
