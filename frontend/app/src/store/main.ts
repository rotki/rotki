import { SemiPartial } from '@rotki/common';
import { Message } from '@rotki/common/lib/messages';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { usePremium } from '@/composables/premium';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { defiSections, Section, Status } from '@/store/const';
import { StatusPayload, Version } from '@/store/types';
import { isLoading } from '@/store/utils';
import { Nullable } from '@/types';
import { LogLevel } from '@/utils/log-level';
import { getDefaultLogLevel, logger, setLevel } from '@/utils/logging';

let intervalId: any = null;
export const useMainStore = defineStore('main', () => {
  const newUser = ref(false);
  const message = ref(emptyMessage());
  const version = ref(defaultVersion());
  const connected = ref(false);
  const connectionFailure = ref(false);
  const status = ref<Partial<Record<Section, Status>>>({});
  const dataDirectory = ref('');
  const logLevel = ref<LogLevel>(getDefaultLogLevel());

  const premium = usePremium();

  const updateNeeded = computed(() => {
    const { version: appVersion, downloadUrl } = get(version);
    return appVersion.indexOf('dev') >= 0 ? false : !!downloadUrl;
  });

  const detailsLoading = computed(() => {
    return (
      isLoading(get(getStatus(Section.BLOCKCHAIN_ETH))) ||
      isLoading(get(getStatus(Section.BLOCKCHAIN_BTC))) ||
      isLoading(get(getStatus(Section.BLOCKCHAIN_KSM))) ||
      isLoading(get(getStatus(Section.BLOCKCHAIN_AVAX))) ||
      isLoading(get(getStatus(Section.EXCHANGES))) ||
      isLoading(get(getStatus(Section.MANUAL_BALANCES)))
    );
  });

  const showMessage = computed(() => get(message).title.length > 0);

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
          const accounts = await api.users();
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

  const setMessage = (
    msg: SemiPartial<Message, 'description'> = emptyMessage()
  ) => {
    set(message, {
      ...{
        title: msg.success
          ? i18n.t('message.success.title').toString()
          : i18n.t('message.error.title').toString(),
        success: false
      },
      ...msg
    });
  };

  const resetDefiStatus = () => {
    const newStatus = Status.NONE;
    defiSections.forEach(section => {
      status.value[section] = newStatus;
    });
  };

  const setStatus = ({ section, status: newStatus }: StatusPayload) => {
    const statuses = get(status);
    if (statuses[section] === newStatus) {
      return;
    }
    set(status, { ...statuses, [section]: newStatus });
  };

  const getStatus = (section: Section) =>
    computed<Status>(() => {
      return get(status)[section] ?? Status.NONE;
    });

  const setConnected = (isConnected: boolean) => {
    set(connected, isConnected);
  };

  const setNewUser = (isNew: boolean) => {
    set(newUser, isNew);
  };

  const setConnectionFailure = (failed: boolean) => {
    set(connectionFailure, failed);
  };

  const reset = () => {
    set(newUser, false);
    set(message, emptyMessage());
    set(version, defaultVersion());
    set(connectionFailure, false);
    set(status, {});
  };

  watch(premium, premium => {
    if (!premium) {
      resetDefiStatus();
    }
  });

  return {
    newUser,
    message,
    version,
    appVersion,
    connected,
    connectionFailure,
    status,
    dataDirectory,
    updateNeeded,
    detailsLoading,
    showMessage,
    connect,
    getVersion,
    getInfo,
    setMessage,
    setStatus,
    getStatus,
    setConnected,
    setConnectionFailure,
    setNewUser,
    resetDefiStatus,
    reset
  };
});
const emptyMessage = (): Message => ({
  title: '',
  description: '',
  success: false
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
