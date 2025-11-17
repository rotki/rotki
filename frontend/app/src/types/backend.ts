import { ActiveLogLevel } from '@shared/ipc';
import { z } from 'zod/v4';

const BackendVersion = z.object({
  downloadUrl: z.string().nullish(),
  latestVersion: z.string().nullish(),
  ourVersion: z.string().optional(),
});
const DefaultBackendArguments = z.object({
  maxLogfilesNum: z.number(),
  maxSizeInMbAllLogs: z.number(),
  sqliteInstructions: z.number(),
});

export type DefaultBackendArguments = z.infer<typeof DefaultBackendArguments>;

export const BackendInfo = z.object({
  acceptDockerRisk: z.boolean(),
  backendDefaultArguments: DefaultBackendArguments,
  dataDirectory: z.string(),
  logLevel: ActiveLogLevel,
  version: BackendVersion,
});

export type BackendInfo = z.infer<typeof BackendInfo>;
const NumericBackendArgument = z.object({
  isDefault: z.boolean(),
  value: z.number().nonnegative(),
});

const LogLevelBackendArgument = z.object({
  isDefault: z.boolean(),
  value: ActiveLogLevel,
});

export const BackendConfiguration = z.object({
  loglevel: LogLevelBackendArgument,
  maxLogfilesNum: NumericBackendArgument,
  maxSizeInMbAllLogs: NumericBackendArgument,
  sqliteInstructions: NumericBackendArgument,
});

export type BackendConfiguration = z.infer<typeof BackendConfiguration>;
