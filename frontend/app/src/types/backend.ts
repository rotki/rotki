import { z } from 'zod';
import { ActiveLogLevel } from '@/electron-main/ipc';

const BackendVersion = z.object({
  ourVersion: z.string().optional(),
  latestVersion: z.string().nullish(),
  downloadUrl: z.string().nullish()
});
const DefaultBackendArguments = z.object({
  maxLogfilesNum: z.number(),
  maxSizeInMbAllLogs: z.number(),
  sqliteInstructions: z.number()
});

export type DefaultBackendArguments = z.infer<typeof DefaultBackendArguments>;

export const BackendInfo = z.object({
  acceptDockerRisk: z.boolean(),
  logLevel: ActiveLogLevel,
  version: BackendVersion,
  dataDirectory: z.string(),
  backendDefaultArguments: DefaultBackendArguments
});

export type BackendInfo = z.infer<typeof BackendInfo>;
const NumericBackendArgument = z.object({
  value: z.number().nonnegative(),
  isDefault: z.boolean()
});

export const BackendConfiguration = z.object({
  maxSizeInMbAllLogs: NumericBackendArgument,
  maxLogfilesNum: NumericBackendArgument,
  sqliteInstructions: NumericBackendArgument
});

export type BackendConfiguration = z.infer<typeof BackendConfiguration>;
