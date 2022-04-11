import { computed, onMounted, ref } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { useInterop } from '@/electron-interop';
import { BackendOptions } from '@/electron-main/ipc';
import { useMainStore } from '@/store/store';
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

export const setupBackendManagement = (loaded: () => void = () => {}) => {
  const interop = useInterop();

  const defaultLogLevel = computed<LogLevel>(() => getDefaultLogLevel());
  const logLevel = ref<LogLevel>(defaultLogLevel.value);
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
    setLevel(options.value.loglevel);
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
    userOptions.value = loadUserOptions();
    fileConfig.value = await interop.config(false);
    const { logDirectory } = await interop.config(true);
    if (logDirectory) {
      defaultLogDirectory.value = logDirectory;
    }
  };

  const saveOptions = async (opts: Partial<BackendOptions>) => {
    const { logDirectory, dataDirectory, loglevel } = userOptions.value;
    const updatedOptions = {
      logDirectory,
      dataDirectory,
      loglevel,
      ...opts
    };
    saveUserOptions(updatedOptions);
    userOptions.value = updatedOptions;
    await restartBackendWithOptions(options.value);
  };

  const resetOptions = async () => {
    saveUserOptions({});
    userOptions.value = {};
    await restartBackendWithOptions(options.value);
  };

  const restartBackend = async () => {
    if (!interop.isPackaged) {
      return;
    }
    await load();
    await restartBackendWithOptions(options.value);
  };

  return {
    logLevel,
    defaultLogLevel,
    options,
    fileConfig,
    saveOptions,
    resetOptions,
    restartBackend
  };
};
