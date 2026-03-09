import type { LogLevel } from '@shared/log-level';
import type { Version } from '@/types/action';
import type { DefaultBackendArguments } from '@/types/backend';
import { checkIfDevelopment } from '@shared/utils';
import { getDefaultLogLevel } from '@/utils/logging';

export const useMainStore = defineStore('main', () => {
  const version = ref<Version>(defaultVersion());
  const connected = ref<boolean>(false);
  const connectionFailure = ref<boolean>(false);
  const connectionEnabled = ref<boolean>(true);
  const dataDirectory = ref<string>('');
  const logLevel = ref<LogLevel>(getDefaultLogLevel());
  const dockerRiskAccepted = ref<boolean>(true);
  const defaultBackendArguments = ref<DefaultBackendArguments>({
    maxLogfilesNum: 0,
    maxSizeInMbAllLogs: 0,
    sqliteInstructions: 0,
  });

  const updateNeeded = computed(() => {
    const { downloadUrl, version: appVersion } = get(version);
    return appVersion.includes('dev') ? false : !!downloadUrl;
  });

  const appVersion = computed(() => {
    const { version: appVersion } = get(version);
    const indexOfDev = appVersion.indexOf('dev');
    return indexOfDev > 0 ? appVersion.slice(0, Math.max(0, indexOfDev + 3)) : appVersion;
  });

  const isDevelop = computed<boolean>(() => {
    const dev = checkIfDevelopment();
    if (dev)
      return true;

    const { version: appVersion } = get(version);
    return appVersion.includes('dev') || get(dataDirectory).includes('develop_data');
  });

  const setConnected = (isConnected: boolean): void => {
    set(connected, isConnected);
  };

  const setConnectionFailure = (failed: boolean): void => {
    set(connectionFailure, failed);
  };

  return {
    appVersion,
    connected,
    connectionEnabled,
    connectionFailure,
    dataDirectory,
    defaultBackendArguments,
    dockerRiskAccepted,
    isDevelop,
    logLevel,
    setConnected,
    setConnectionFailure,
    updateNeeded,
    version,
  };
});

function defaultVersion(): Version {
  return {
    downloadUrl: '',
    latestVersion: '',
    version: '',
  };
}

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useMainStore, import.meta.hot));
