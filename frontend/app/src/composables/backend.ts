import { useInterop } from '@/electron-interop';
import { BackendOptions } from '@/electron-main/ipc';
import { useMainStore } from '@/store/main';
import { Writeable } from '@/types';
import { LogLevel } from '@/utils/log-level';
import { getDefaultLogLevel, setLevel } from '@/utils/logging';

const BACKEND_OPTIONS = 'BACKEND_OPTIONS';

export const loadUserOptions: () => Partial<BackendOptions> = () => {
  const defaultConfig: Partial<BackendOptions> = {
    loglevel: getDefaultLogLevel()
  };
  try {
    const opts = localStorage.getItem(BACKEND_OPTIONS);
    let options: Writeable<Partial<BackendOptions>>;
    if (opts) {
      options = BackendOptions.parse(JSON.parse(opts));
    } else {
      options = defaultConfig;
    }
    return options;
  } catch (e) {
    return defaultConfig;
  }
};

export const saveUserOptions = (config: Partial<BackendOptions>) => {
  const options = JSON.stringify(config);
  localStorage.setItem(BACKEND_OPTIONS, options);
};

export const useBackendManagement = (loaded: () => void = () => {}) => {
  const interop = useInterop();

  const defaultLogLevel = computed<LogLevel>(() => getDefaultLogLevel());
  const logLevel = ref<LogLevel>(get(defaultLogLevel));
  const userOptions = ref<Partial<BackendOptions>>({});
  const fileConfig = ref<Partial<BackendOptions>>({});
  const defaultLogDirectory = ref('');
  const options = computed<Partial<BackendOptions>>(() => ({
    ...get(userOptions),
    ...get(fileConfig)
  }));

  onMounted(async () => {
    await load();
    loaded();
    setLevel(get(options).loglevel);
  });

  const restartBackendWithOptions = async (
    options: Partial<BackendOptions>
  ) => {
    const { setConnected, connect } = useMainStore();
    await setConnected(false);
    await interop.restartBackend(options);
    await connect();
  };

  const load = async () => {
    if (!interop.isPackaged) {
      return;
    }
    set(userOptions, loadUserOptions());
    set(fileConfig, await interop.config(false));
    const { logDirectory } = await interop.config(true);
    if (logDirectory) {
      set(defaultLogDirectory, logDirectory);
    }
  };

  const saveOptions = async (opts: Partial<BackendOptions>) => {
    const { logDirectory, dataDirectory, loglevel } = get(userOptions);
    const updatedOptions = {
      logDirectory,
      dataDirectory,
      loglevel,
      ...opts
    };
    saveUserOptions(updatedOptions);
    set(userOptions, updatedOptions);
    await restartBackendWithOptions(get(options));
  };

  const resetOptions = async () => {
    saveUserOptions({});
    set(userOptions, {});
    await restartBackendWithOptions(get(options));
  };

  const restartBackend = async () => {
    if (!interop.isPackaged) {
      return;
    }
    await load();
    await restartBackendWithOptions(get(options));
  };

  return {
    logLevel,
    defaultLogLevel,
    defaultLogDirectory,
    options,
    fileConfig,
    saveOptions,
    resetOptions,
    restartBackend
  };
};
