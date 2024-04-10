import { BackendOptions } from '@/electron-main/ipc';
import type { Writeable } from '@/types';
import type { LogLevel } from '@/utils/log-level';

const BACKEND_OPTIONS = 'BACKEND_OPTIONS';

export const loadUserOptions: () => Partial<BackendOptions> = () => {
  const defaultConfig: Partial<BackendOptions> = {
    loglevel: getDefaultLogLevel(),
  };
  try {
    const opts = localStorage.getItem(BACKEND_OPTIONS);
    let options: Writeable<Partial<BackendOptions>>;
    if (opts)
      options = BackendOptions.parse(JSON.parse(opts));
    else
      options = defaultConfig;

    return options;
  }
  catch {
    return defaultConfig;
  }
};

export function saveUserOptions(config: Partial<BackendOptions>) {
  const options = JSON.stringify(config);
  localStorage.setItem(BACKEND_OPTIONS, options);
}

export function useBackendManagement(loaded: () => void = () => {}) {
  const interop = useInterop();
  const store = useMainStore();
  const { connected } = storeToRefs(store);
  const { setConnected, connect } = store;

  const defaultLogLevel = computed<LogLevel>(() => getDefaultLogLevel());
  const logLevel = ref<LogLevel>(get(defaultLogLevel));
  const userOptions = ref<Partial<BackendOptions>>({});
  const fileConfig = ref<Partial<BackendOptions>>({});
  const defaultLogDirectory = ref('');
  const options = computed<Partial<BackendOptions>>(() => ({
    ...get(userOptions),
    ...get(fileConfig),
  }));

  const restartBackendWithOptions = async (
    options: Partial<BackendOptions>,
  ) => {
    setConnected(false);
    await interop.restartBackend(options);
    connect();
  };

  const load = async () => {
    if (!interop.isPackaged)
      return;

    set(userOptions, loadUserOptions());
    set(fileConfig, await interop.config(false));
    const { logDirectory } = await interop.config(true);
    if (logDirectory)
      set(defaultLogDirectory, logDirectory);
  };

  const applyUserOptions = async (config: Partial<BackendOptions>) => {
    saveUserOptions(config);
    set(userOptions, config);
    await restartBackendWithOptions(get(options));
  };

  const saveOptions = async (opts: Partial<BackendOptions>) => {
    const { logDirectory, dataDirectory, loglevel } = get(userOptions);
    const updatedOptions = {
      logDirectory,
      dataDirectory,
      loglevel,
      ...opts,
    };
    await applyUserOptions(updatedOptions);
  };

  const resetOptions = async () => {
    await applyUserOptions({});
  };

  const restartBackend = async () => {
    if (!interop.isPackaged)
      return;

    await load();
    await restartBackendWithOptions(get(options));
  };

  const resetSessionBackend = async () => {
    const { sessionOnly } = getBackendUrl();
    if (sessionOnly) {
      deleteBackendUrl();
      await restartBackend();
    }
  };

  const backendChanged = async (url: string | null) => {
    setConnected(false);
    if (!url)
      await restartBackend();

    connect(url);
  };

  const setupBackend = async () => {
    if (get(connected))
      return;

    const { sessionOnly, url } = getBackendUrl();
    if (!!url && !sessionOnly)
      await backendChanged(url);
    else
      await restartBackend();
  };

  onMounted(() => {
    load().then(() => {
      loaded();
      setLevel(get(options).loglevel);
    }).catch(error => logger.error(error));
  });

  return {
    logLevel,
    defaultLogLevel,
    defaultLogDirectory,
    options,
    fileConfig,
    saveOptions,
    resetOptions,
    restartBackend,
    resetSessionBackend,
    setupBackend,
    backendChanged,
  };
}
