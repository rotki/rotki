import { type Ref } from 'vue';
import { api } from '@/services/rotkehlchen-api';
import { useUsersApi } from '@/services/session/users.api';
import { type Version } from '@/store/types';
import { type Nullable } from '@/types';
import { type LogLevel } from '@/utils/log-level';
import { getDefaultLogLevel, logger, setLevel } from '@/utils/logging';

let intervalId: any = null;
export const useMainStore = defineStore('main', () => {
  const newUser: Ref<boolean> = ref(false);
  const version: Ref<Version> = ref(defaultVersion());
  const connected: Ref<boolean> = ref(false);
  const connectionFailure: Ref<boolean> = ref(false);
  const dataDirectory: Ref<string> = ref('');
  const logLevel: Ref<LogLevel> = ref(getDefaultLogLevel());
  const dockerRiskAccepted: Ref<boolean> = ref(true);

  const usersApi = useUsersApi();

  const updateNeeded = computed(() => {
    const { version: appVersion, downloadUrl } = get(version);
    return appVersion.includes('dev') ? false : !!downloadUrl;
  });

  const appVersion = computed(() => {
    const { version: appVersion } = get(version);
    const indexOfDev = appVersion.indexOf('dev');
    return indexOfDev > 0
      ? appVersion.slice(0, Math.max(0, indexOfDev + 3))
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
    const {
      dataDirectory: appDataDirectory,
      logLevel: level,
      acceptDockerRisk
    } = await api.info(false);
    set(dataDirectory, appDataDirectory);
    set(logLevel, level);
    set(dockerRiskAccepted, acceptDockerRisk);
    setLevel(level);
  };

  const connect = async (payload?: string | null): Promise<void> => {
    let count = 0;
    if (intervalId) {
      clearInterval(intervalId);
    }

    const updateApi = (payload?: Nullable<string>): void => {
      const interopBackendUrl = window.interop?.serverUrl();
      let backendUrl = api.defaultServerUrl;
      if (payload) {
        backendUrl = payload;
      } else if (interopBackendUrl) {
        backendUrl = interopBackendUrl;
      }
      api.setup(backendUrl);
    };

    const attemptConnect = async (): Promise<void> => {
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

  const setConnected = (isConnected: boolean): void => {
    set(connected, isConnected);
  };

  const setNewUser = (isNew: boolean): void => {
    set(newUser, isNew);
  };

  const setConnectionFailure = (failed: boolean): void => {
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
    dockerRiskAccepted,
    connect,
    getVersion,
    getInfo,
    setConnected,
    setConnectionFailure,
    setNewUser
  };
});

const defaultVersion = (): Version => ({
  version: '',
  latestVersion: '',
  downloadUrl: ''
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useMainStore, import.meta.hot));
}
