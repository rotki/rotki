import { api } from '@/services/rotkehlchen-api';
import { useUsersApi } from '@/services/session/users.api';
import { Version } from '@/store/types';
import { Nullable } from '@/types';
import { LogLevel } from '@/utils/log-level';
import { getDefaultLogLevel, logger, setLevel } from '@/utils/logging';

let intervalId: any = null;
export const useMainStore = defineStore('main', () => {
  const newUser = ref(false);
  const version = ref(defaultVersion());
  const connected = ref(false);
  const connectionFailure = ref(false);
  const dataDirectory = ref('');
  const logLevel = ref<LogLevel>(getDefaultLogLevel());

  const usersApi = useUsersApi();

  const updateNeeded = computed(() => {
    const { version: appVersion, downloadUrl } = get(version);
    return appVersion.indexOf('dev') >= 0 ? false : !!downloadUrl;
  });

  const appVersion = computed(() => {
    const { version: appVersion } = get(version);
    const indexOfDev = appVersion.indexOf('dev');
    return indexOfDev > 0
      ? appVersion.substring(0, indexOfDev + 3)
      : appVersion;
  });

  const getVersion = async (): Promise<void> => {
    const { version: appVersion } = await api.info(true);
    if (appVersion) {
      set(version, {
        version: appVersion.ourVersion || '',
        latestVersion: appVersion.latestVersion || '',
        downloadUrl: appVersion.downloadUrl || ''
      });
    }
  };

  const getInfo = async (): Promise<void> => {
    const { dataDirectory: appDataDirectory, logLevel: level } = await api.info(
      false
    );
    set(dataDirectory, appDataDirectory);
    set(logLevel, level);
    setLevel(level);
  };

  const connect = async (payload?: string | null): Promise<void> => {
    let count = 0;
    if (intervalId) {
      clearInterval(intervalId);
    }

    function updateApi(payload?: Nullable<string>) {
      const interopBackendUrl = window.interop?.serverUrl();
      let backendUrl = api.defaultServerUrl;
      if (payload) {
        backendUrl = payload;
      } else if (interopBackendUrl) {
        backendUrl = interopBackendUrl;
      }
      api.setup(backendUrl);
    }

    const attemptConnect = async function () {
      try {
        updateApi(payload);

        const isConnected = !!(await api.ping());
        if (isConnected) {
          const accounts = await usersApi.users();
          if (accounts.length === 0) {
            set(newUser, true);
          }
          clearInterval(intervalId);
          set(connected, isConnected);

          await getInfo();
          await getVersion();
        }
      } catch (e: any) {
        logger.error(e);
      } finally {
        count++;
        if (count > 20) {
          clearInterval(intervalId);
          set(connectionFailure, true);
        }
      }
    };
    intervalId = setInterval(attemptConnect, 2000);
    set(connectionFailure, false);
  };

  const setConnected = (isConnected: boolean) => {
    set(connected, isConnected);
  };

  const setNewUser = (isNew: boolean) => {
    set(newUser, isNew);
  };

  const setConnectionFailure = (failed: boolean) => {
    set(connectionFailure, failed);
  };

  return {
    newUser,
    version,
    appVersion,
    connected,
    connectionFailure,
    dataDirectory,
    updateNeeded,
    connect,
    getVersion,
    getInfo,
    setConnected,
    setConnectionFailure,
    setNewUser
  };
});

const defaultVersion = () =>
  ({
    version: '',
    latestVersion: '',
    downloadUrl: ''
  } as Version);

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useMainStore, import.meta.hot));
}
