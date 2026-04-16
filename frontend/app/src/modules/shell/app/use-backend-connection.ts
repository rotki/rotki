import type { Nullable } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { apiUrls, defaultApiUrls } from '@/modules/core/api/api-urls';
import { api } from '@/modules/core/api/rotki-api';
import { logger, setLevel } from '@/modules/core/common/logging/logging';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useInfoApi } from '@/modules/shell/app/use-info-api';

interface UseBackendConnectionReturn {
  cancelConnectionAttempts: () => void;
  connect: (payload?: string | null) => void;
  getInfo: () => Promise<void>;
  getVersion: () => Promise<void>;
  stopConnectionAttempts: () => void;
}

export function useBackendConnection(): UseBackendConnectionReturn {
  let intervalId: NodeJS.Timeout | undefined;

  const store = useMainStore();
  const {
    connected,
    connectionEnabled,
    connectionFailure,
    dataDirectory,
    defaultBackendArguments,
    dockerRiskAccepted,
    logLevel,
    version,
  } = storeToRefs(store);

  const { info, ping } = useInfoApi();

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

  const cancelConnectionAttempts = (): void => {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = undefined;
      logger.debug('Connection attempts cancelled');
    }
  };

  const stopConnectionAttempts = (): void => {
    set(connectionEnabled, false);
    cancelConnectionAttempts();
    logger.debug('Connection attempts stopped and disabled');
  };

  const connect = (payload?: string | null): void => {
    if (!get(connectionEnabled)) {
      logger.debug('Connection skipped - connection disabled');
      return;
    }

    let count = 0;
    if (intervalId)
      clearInterval(intervalId);

    const updateApi = (payload?: Nullable<string>): void => {
      const updatedUrls = typeof window !== 'undefined' ? window.interop?.apiUrls() : undefined;
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
        const isConnected = await ping();
        if (isConnected) {
          clearInterval(intervalId);
          set(connected, isConnected);

          await getInfo();
          await getVersion();
        }
      }
      catch (error: unknown) {
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
    updateApi(payload);
    intervalId = setInterval(() => startPromise(attemptConnect()), 2000);
    set(connectionFailure, false);
  };

  onScopeDispose(() => {
    if (!intervalId) {
      return;
    }
    clearInterval(intervalId);
    intervalId = undefined;
  });

  return {
    cancelConnectionAttempts,
    connect,
    getInfo,
    getVersion,
    stopConnectionAttempts,
  };
}
