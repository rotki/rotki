import type { BackendOptions } from '@shared/ipc';
import type { LogLevel } from '@shared/log-level';
import type { ComputedRef, DeepReadonly, Ref } from 'vue';
import { deleteBackendUrl, getBackendUrl } from '@/modules/auth/account-management';
import { getDefaultLogLevel, logger, setLevel } from '@/modules/core/common/logging/logging';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useControl } from '@/modules/core/control/use-control';
import { clearUserOptions, loadUserOptions, saveUserOptions } from '@/modules/shell/app/backend-options';
import { useBackendConnection } from '@/modules/shell/app/use-backend-connection';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { useWebsocketConnection } from '@/modules/shell/app/use-websocket-connection';

interface UseBackendManagementReturn {
  applyUserOptions: (config: Partial<BackendOptions>, skipRestart: boolean) => Promise<void>;
  modelLogLevel: Ref<LogLevel>;
  defaultLogLevel: ComputedRef<LogLevel>;
  defaultLogDirectory: Readonly<Ref<string>>;
  options: ComputedRef<Partial<BackendOptions>>;
  fileConfig: DeepReadonly<Ref<Partial<BackendOptions>>>;
  saveOptions: (opts: Partial<BackendOptions>) => Promise<void>;
  resetOptions: () => Promise<void>;
  restartBackend: (forceRestart?: boolean) => Promise<void>;
  resetSessionBackend: () => Promise<void>;
  setupBackend: () => Promise<void>;
  backendChanged: (url: string | null) => Promise<void>;
}

export function useBackendManagement(loaded: () => void = () => {}): UseBackendManagementReturn {
  const interop = useInterop();
  const store = useMainStore();
  const { connected, connectionEnabled } = storeToRefs(store);
  const { setConnected } = store;
  const { connect } = useBackendConnection();
  const { setConnectionEnabled: setWsConnectionEnabled } = useWebsocketConnection();
  const { probe: controlProbe, restart: controlRestart } = useControl();

  const defaultLogLevel = computed<LogLevel>(() => getDefaultLogLevel());
  const modelLogLevel = ref<LogLevel>(get(defaultLogLevel));
  const userOptions = ref<Partial<BackendOptions>>({});
  const fileConfig = ref<Partial<BackendOptions>>({});
  const defaultLogDirectory = shallowRef<string>('');
  const options = computed<Partial<BackendOptions>>(() => ({
    ...get(userOptions),
    ...get(fileConfig),
  }));

  const restartBackendWithOptions = async (options: Partial<BackendOptions>, forceRestart = false): Promise<void> => {
    setConnected(false);
    await interop.restartBackend(options, forceRestart);
    // Re-enable connections in case a prior process termination disabled them
    // (e.g. on Windows, taskkill exits the core process with a non-zero code, which
    // is reported as a TERMINATED startup error and disables connection attempts).
    set(connectionEnabled, true);
    setWsConnectionEnabled(true);
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
    const resolvedLevel = get(options).loglevel;
    setLevel(resolvedLevel);
    if (resolvedLevel && interop.isPackaged) {
      interop.setLogLevel(resolvedLevel);
    }
    if (!skipRestart) {
      await restartBackendWithOptions(get(options), true);
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
    await restartBackendWithOptions(get(options), true);
  };

  const restartBackend = async (forceRestart = false): Promise<void> => {
    if (interop.isPackaged) {
      await load();
      await restartBackendWithOptions(get(options), forceRestart);
      return;
    }

    // Docker: no Electron to ask, but starling exposes the same `restart` over
    // `/_control` once a session cookie is configured (#2807). Until this
    // existed the call simply returned, so every flow that needs a bounced
    // backend — the asset-update unlock step, AssetUpdate, RestoreAssetDbButton
    // — silently did nothing in a container. `available` is false where there is
    // no control endpoint, which keeps the old no-op for the plain web build.
    if (!await controlProbe())
      return;

    setConnected(false);
    try {
      await controlRestart();
    }
    catch (error: unknown) {
      // Never propagate: callers treat a restart as a step in a longer sequence
      // and follow it with a reconnect, so throwing here would strand the UI
      // mid-flow. The common cause is a caller that logged out first, which
      // revokes the cookie the control endpoint authorises against.
      logger.error(error);
    }
    set(connectionEnabled, true);
    setWsConnectionEnabled(true);
    connect();
  };

  const resetSessionBackend = async (): Promise<void> => {
    const { sessionOnly } = getBackendUrl();
    if (sessionOnly) {
      deleteBackendUrl();
      await restartBackend(true);
    }
  };

  const backendChanged = async (url: string | null): Promise<void> => {
    setConnected(false);
    if (!url)
      await restartBackend(true);

    connect(url);
  };

  const setupBackend = async (): Promise<void> => {
    if (get(connected))
      return;

    const { sessionOnly, url } = getBackendUrl();
    if (!!url && !sessionOnly) {
      await backendChanged(url);
    }
    // Boot only *starts* a backend where the app owns one. In docker the tree is
    // already up before the page loads, so restarting here would bounce it on
    // every reload — and before login the control endpoint would refuse anyway,
    // stranding the user short of the login screen. Explicit restart flows call
    // `restartBackend` directly; boot is not one of them.
    else if (interop.isPackaged) {
      await restartBackend();
    }

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
    defaultLogDirectory: readonly(defaultLogDirectory),
    defaultLogLevel,
    fileConfig: readonly(fileConfig),
    modelLogLevel,
    options,
    resetOptions,
    resetSessionBackend,
    restartBackend,
    saveOptions,
    setupBackend,
  };
}
