import type { BackendOptions } from '@shared/ipc';
import type { LogLevel } from '@shared/log-level';
import type { ComputedRef, Ref } from 'vue';
import { deleteBackendUrl, getBackendUrl } from '@/modules/auth/account-management';
import { getDefaultLogLevel, logger, setLevel } from '@/modules/core/common/logging/logging';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { clearUserOptions, loadUserOptions, saveUserOptions } from '@/modules/shell/app/backend-options';
import { useBackendConnection } from '@/modules/shell/app/use-backend-connection';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

interface UseBackendManagementReturn {
  applyUserOptions: (config: Partial<BackendOptions>, skipRestart: boolean) => Promise<void>;
  logLevel: Ref<LogLevel>;
  defaultLogLevel: ComputedRef<LogLevel>;
  defaultLogDirectory: Ref<string>;
  options: ComputedRef<Partial<BackendOptions>>;
  fileConfig: Ref<Partial<BackendOptions>>;
  saveOptions: (opts: Partial<BackendOptions>) => Promise<void>;
  resetOptions: () => Promise<void>;
  restartBackend: () => Promise<void>;
  resetSessionBackend: () => Promise<void>;
  setupBackend: () => Promise<void>;
  backendChanged: (url: string | null) => Promise<void>;
}

export function useBackendManagement(loaded: () => void = () => {}): UseBackendManagementReturn {
  const interop = useInterop();
  const store = useMainStore();
  const { connected } = storeToRefs(store);
  const { setConnected } = store;
  const { connect } = useBackendConnection();

  const defaultLogLevel = computed<LogLevel>(() => getDefaultLogLevel());
  const logLevel = ref<LogLevel>(get(defaultLogLevel));
  const userOptions = ref<Partial<BackendOptions>>({});
  const fileConfig = ref<Partial<BackendOptions>>({});
  const defaultLogDirectory = shallowRef<string>('');
  const options = computed<Partial<BackendOptions>>(() => ({
    ...get(userOptions),
    ...get(fileConfig),
  }));

  const restartBackendWithOptions = async (options: Partial<BackendOptions>): Promise<void> => {
    setConnected(false);
    await interop.restartBackend(options);
    connect();
  };

  const load = async (): Promise<void> => {
    if (!interop.isPackaged)
      return;

    set(userOptions, loadUserOptions());
    set(fileConfig, await interop.config(false));
    const { logDirectory } = await interop.config(true);
    if (logDirectory)
      set(defaultLogDirectory, logDirectory);
  };

  const applyUserOptions = async (config: Partial<BackendOptions>, skipRestart = false): Promise<void> => {
    saveUserOptions(config);
    set(userOptions, config);
    setLevel(get(options).loglevel);
    if (!skipRestart) {
      await restartBackendWithOptions(get(options));
    }
  };

  const saveOptions = async (opts: Partial<BackendOptions>): Promise<void> => {
    const { dataDirectory, logDirectory, loglevel } = get(userOptions);
    const updatedOptions = {
      dataDirectory,
      logDirectory,
      loglevel,
      ...opts,
    };
    await applyUserOptions(updatedOptions);
  };

  const resetOptions = async (): Promise<void> => {
    clearUserOptions();
    set(userOptions, {});
    await restartBackendWithOptions(get(options));
  };

  const restartBackend = async (): Promise<void> => {
    if (!interop.isPackaged)
      return;

    await load();
    await restartBackendWithOptions(get(options));
  };

  const resetSessionBackend = async (): Promise<void> => {
    const { sessionOnly } = getBackendUrl();
    if (sessionOnly) {
      deleteBackendUrl();
      await restartBackend();
    }
  };

  const backendChanged = async (url: string | null): Promise<void> => {
    setConnected(false);
    if (!url)
      await restartBackend();

    connect(url);
  };

  const setupBackend = async (): Promise<void> => {
    if (get(connected))
      return;

    const { sessionOnly, url } = getBackendUrl();
    if (!!url && !sessionOnly)
      await backendChanged(url);
    else
      await restartBackend();

    if (!interop.isPackaged)
      connect();
  };

  onMounted(() => {
    load()
      .then(() => {
        loaded();
        setLevel(get(options).loglevel);
      })
      .catch(error => logger.error(error));
  });

  return {
    applyUserOptions,
    backendChanged,
    defaultLogDirectory,
    defaultLogLevel,
    fileConfig,
    logLevel,
    options,
    resetOptions,
    resetSessionBackend,
    restartBackend,
    saveOptions,
    setupBackend,
  };
}
