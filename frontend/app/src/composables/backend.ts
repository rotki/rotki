import { computed, onMounted, ref, unref } from '@vue/composition-api';
import { useInterop } from '@/electron-interop';
import { BackendOptions } from '@/electron-main/ipc';
import { useMainStore } from '@/store/store';
import { Writeable } from '@/types';
import { CRITICAL, DEBUG, ERROR, Level, LOG_LEVEL } from '@/utils/log-level';
import { logger } from '@/utils/logging';

const BACKEND_OPTIONS = 'BACKEND_OPTIONS';

export const loadUserOptions: () => Partial<BackendOptions> = () => {
  const defaultConfig: Partial<BackendOptions> = {
    loglevel: process.env.NODE_ENV === 'development' ? DEBUG : CRITICAL
  };
  try {
    const opts = localStorage.getItem(BACKEND_OPTIONS);
    const options: Writeable<Partial<BackendOptions>> = opts
      ? JSON.parse(opts)
      : defaultConfig;
    const loglevel = localStorage.getItem(LOG_LEVEL);
    if (loglevel) {
      options.loglevel = loglevel as Level;
      saveUserOptions(options);
      localStorage.removeItem(LOG_LEVEL);
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

  const defaultLogLevel = computed<Level>(() =>
    process.env.NODE_ENV === 'development' ? DEBUG : CRITICAL
  );
  const logLevel = ref<Level>(defaultLogLevel.value);
  const userOptions = ref<Partial<BackendOptions>>({});
  const fileConfig = ref<Partial<BackendOptions>>({});
  const defaultLogDirectory = ref('');
  const options = computed<Partial<BackendOptions>>(() => ({
    ...unref(userOptions),
    ...unref(fileConfig)
  }));

  onMounted(async () => {
    await load();
    loaded();
    const loglevel = options.value.loglevel;
    const level: Exclude<Level, 'critical'> =
      !loglevel || loglevel === CRITICAL ? ERROR : loglevel;
    logger.setDefaultLevel(level);
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
