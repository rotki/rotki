import { NumericString } from '@rotki/common';
import { SupportedAsset } from '@rotki/common/lib/data';
import { z } from 'zod';
import { ActiveLogLevel } from '@/electron-main/ipc';

export const SYNC_UPLOAD = 'upload';
export const SYNC_DOWNLOAD = 'download';

const SYNC_ACTIONS = [SYNC_DOWNLOAD, SYNC_UPLOAD] as const;

export type SyncAction = typeof SYNC_ACTIONS[number];

export const SupportedAssets = z.object({
  entries: z.array(SupportedAsset),
  entriesFound: z.number(),
  entriesLimit: z.number().default(-1),
  entriesTotal: z.number(),
  totalUsdValue: NumericString.nullish()
});

export type SupportedAssets = z.infer<typeof SupportedAssets>;

export class TaskNotFoundError extends Error {
  constructor(msg: string) {
    super(msg);
    this.name = 'TaskNotFoundError';
  }
}

export interface PendingTask {
  readonly taskId: number;
}

const BackendVersion = z.object({
  ourVersion: z.string().optional(),
  latestVersion: z.string().nullish(),
  downloadUrl: z.string().nullish()
});

export const BackendInfo = z.object({
  acceptDockerRisk: z.boolean(),
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
