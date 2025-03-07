import type { Version } from '@/types/action';
import type { DefaultBackendArguments } from '@/types/backend';
import type { Nullable } from '@rotki/common';
import type { LogLevel } from '@shared/log-level';
import { useInfoApi } from '@/composables/api/info';
import { apiUrls, defaultApiUrls } from '@/services/api-urls';
import { api } from '@/services/rotkehlchen-api';
import { getDefaultLogLevel, logger, setLevel } from '@/utils/logging';
import { checkIfDevelopment, startPromise } from '@shared/utils';

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

  const getVersion = async (): Promise<void> => {
    const { version: appVersion } = await info(true);
    if (appVersion) {
      set(version, {
        downloadUrl: appVersion.downloadUrl ?? '',
        latestVersion: appVersion.latestVersion ?? '',
        version: appVersion.ourVersion ?? '',
      });
    }
  };

  const getInfo = async (): Promise<void> => {
    const {
      acceptDockerRisk,
      backendDefaultArguments,
      dataDirectory: appDataDirectory,
      logLevel: level,
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
      const updatedUrls = window.interop?.apiUrls();
      let backendUrl = defaultApiUrls.coreApiUrl;
      if (payload) {
        backendUrl = payload;
      }
      else if (updatedUrls) {
        backendUrl = updatedUrls.coreApiUrl;
        apiUrls.coreApiUrl = updatedUrls.coreApiUrl;
        apiUrls.colibriApiUrl = updatedUrls.colibriApiUrl;
      }

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
    appVersion,
    connect,
    connected,
    connectionFailure,
    dataDirectory,
    defaultBackendArguments,
    dockerRiskAccepted,
    getInfo,
    getVersion,
    isDevelop,
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
