import { api } from '@/services/rotkehlchen-api';
import type { Nullable } from '@rotki/common';
import type { LogLevel } from '@shared/log-level';
import type { Version } from '@/types/action';
import type { DefaultBackendArguments } from '@/types/backend';

let intervalId: any = null;

export const useMainStore = defineStore('main', () => {
  const version = ref<Version>(defaultVersion());
  const connected = ref<boolean>(false);
  const connectionFailure = ref<boolean>(false);
  const dataDirectory = ref<string>('');
  const logLevel = ref<LogLevel>(getDefaultLogLevel());
  const dockerRiskAccepted = ref<boolean>(true);
  const defaultBackendArguments = ref<DefaultBackendArguments>({
    maxLogfilesNum: 0,
    maxSizeInMbAllLogs: 0,
    sqliteInstructions: 0,
  });

  const { info, ping } = useInfoApi();

  const updateNeeded = computed(() => {
    const { version: appVersion, downloadUrl } = get(version);
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

  const getVersion = async (): Promise<void> => {
    const { version: appVersion } = await info(true);
    if (appVersion) {
      set(version, {
        version: appVersion.ourVersion || '',
        latestVersion: appVersion.latestVersion || '',
        downloadUrl: appVersion.downloadUrl || '',
      });
    }
  };

  const getInfo = async (): Promise<void> => {
    const {
      dataDirectory: appDataDirectory,
      logLevel: level,
      acceptDockerRisk,
      backendDefaultArguments,
    } = await info(false);

    set(dataDirectory, appDataDirectory);
    set(logLevel, level);
    set(dockerRiskAccepted, acceptDockerRisk);
    setLevel(level);
    set(defaultBackendArguments, backendDefaultArguments);
  };

  const connect = (payload?: string | null): void => {
    let count = 0;
    if (intervalId)
      clearInterval(intervalId);

    const updateApi = (payload?: Nullable<string>): void => {
      const interopBackendUrl = window.interop?.serverUrl();
      let backendUrl = api.defaultServerUrl;
      if (payload)
        backendUrl = payload;
      else if (interopBackendUrl)
        backendUrl = interopBackendUrl;

      api.setup(backendUrl);
    };

    const attemptConnect = async (): Promise<void> => {
      try {
        updateApi(payload);

        const isConnected = !!(await ping());
        if (isConnected) {
          clearInterval(intervalId);
          set(connected, isConnected);

          await getInfo();
          await getVersion();
        }
      }
      catch (error: any) {
        logger.error(error);
      }
      finally {
        count++;
        if (count > 20) {
          clearInterval(intervalId);
          set(connectionFailure, true);
        }
      }
    };
    intervalId = setInterval(() => startPromise(attemptConnect()), 2000);
    set(connectionFailure, false);
  };

  const setConnected = (isConnected: boolean): void => {
    set(connected, isConnected);
  };

  const setConnectionFailure = (failed: boolean): void => {
    set(connectionFailure, failed);
  };

  return {
    version,
    appVersion,
    connected,
    connectionFailure,
    dataDirectory,
    updateNeeded,
    dockerRiskAccepted,
    defaultBackendArguments,
    isDevelop,
    connect,
    getVersion,
    getInfo,
    setConnected,
    setConnectionFailure,
  };
});

function defaultVersion(): Version {
  return {
    version: '',
    latestVersion: '',
    downloadUrl: '',
  };
}

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useMainStore, import.meta.hot));
