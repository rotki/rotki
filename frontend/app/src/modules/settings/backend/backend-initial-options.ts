import type { BackendOptions } from '@shared/ipc';
import type { BackendConfiguration, DefaultBackendArguments } from '@/modules/shell/app/backend';

export interface BackendOptionFallbacks {
  dataDirectory: string;
  logDirectory: string;
  defaultLogLevel: BackendOptions['loglevel'];
  defaults: DefaultBackendArguments;
}

/**
 * Flattens the backend configuration to its bare `.value`s (or `undefined`),
 * so the precedence resolution below stays free of optional-chaining noise.
 */
function extractConfiguredValues(configuration?: BackendConfiguration): {
  loglevel?: BackendOptions['loglevel'];
  maxLogfilesNum?: number;
  maxSizeInMbAllLogs?: number;
  sqliteInstructions?: number;
} {
  return {
    loglevel: configuration?.loglevel?.value,
    maxLogfilesNum: configuration?.maxLogfilesNum?.value,
    maxSizeInMbAllLogs: configuration?.maxSizeInMbAllLogs?.value,
    sqliteInstructions: configuration?.sqliteInstructions?.value,
  };
}

function resolveDirectoryOptions(options: Partial<BackendOptions>, fallbacks: BackendOptionFallbacks): Partial<BackendOptions> {
  return {
    dataDirectory: options.dataDirectory ?? fallbacks.dataDirectory,
    logDirectory: options.logDirectory ?? fallbacks.logDirectory,
    logFromOtherModules: options.logFromOtherModules ?? false,
  };
}

function resolveConfigBackedOptions(
  options: Partial<BackendOptions>,
  configured: ReturnType<typeof extractConfiguredValues>,
  fallbacks: BackendOptionFallbacks,
): Partial<BackendOptions> {
  return {
    loglevel: options.loglevel ?? configured.loglevel ?? fallbacks.defaultLogLevel,
    maxLogfilesNum: options.maxLogfilesNum ?? configured.maxLogfilesNum ?? fallbacks.defaults.maxLogfilesNum,
    maxSizeInMbAllLogs: options.maxSizeInMbAllLogs ?? configured.maxSizeInMbAllLogs ?? fallbacks.defaults.maxSizeInMbAllLogs,
    sqliteInstructions: options.sqliteInstructions ?? configured.sqliteInstructions ?? fallbacks.defaults.sqliteInstructions,
  };
}

/**
 * Resolves the initial backend options shown in the onboarding form.
 * Precedence per field: persisted user option, then backend configuration,
 * then the environment fallback/default.
 */
export function resolveInitialBackendOptions(
  options: Partial<BackendOptions>,
  configuration: BackendConfiguration | undefined,
  fallbacks: BackendOptionFallbacks,
): Partial<BackendOptions> {
  const configured = extractConfiguredValues(configuration);
  return {
    ...resolveDirectoryOptions(options, fallbacks),
    ...resolveConfigBackedOptions(options, configured, fallbacks),
  };
}
