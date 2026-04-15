import type { LogLevel } from '@shared/log-level';
import type { DefaultBackendArguments } from '@/modules/app/backend';
import type { Version } from '@/modules/common/action';
import { checkIfDevelopment } from '@shared/utils';
import { getDefaultLogLevel } from '@/utils/logging';

export const useMainStore = defineStore('main', () => {
  const version = ref<Version>(defaultVersion());
  const connected = ref<boolean>(false);
  const connectionFailure = ref<boolean>(false);
  const connectionEnabled = ref<boolean>(true);
  const dataDirectory = ref<string>('');
  const logLevel = ref<LogLevel>(getDefaultLogLevel());
  const dockerRiskAccepted = ref<boolean>(true);
  const defaultBackendArguments = ref<DefaultBackendArguments>({
    maxLogfilesNum: 0,
    maxSizeInMbAllLogs: 0,
    sqliteInstructions: 0,
  });

  const updateNeeded = computed(() => {
    const { downloadUrl, version: appVersion } = get(version);
    return appVersion.includes('dev') ? false : !!downloadUrl;
  });

  const appVersion = computed<string>(() => {
    const { version: rawVersion } = get(version);
    const indexOfDev = rawVersion.indexOf('dev');
    const baseVersion = indexOfDev > 0 ? rawVersion.slice(0, Math.max(0, indexOfDev + 3)) : rawVersion;
    return applyDemoMode(baseVersion);
  });

  const isDevelop = computed<boolean>(() => {
    const dev = checkIfDevelopment();
    if (dev)
      return true;

    const { version: appVersion } = get(version);
    return appVersion.includes('dev') || get(dataDirectory).includes('develop_data');
  });

  const setConnected = (isConnected: boolean): void => {
    set(connected, isConnected);
  };

  const setConnectionFailure = (failed: boolean): void => {
    set(connectionFailure, failed);
  };

  return {
    appVersion,
    connected,
    connectionEnabled,
    connectionFailure,
    dataDirectory,
    defaultBackendArguments,
    dockerRiskAccepted,
    isDevelop,
    logLevel,
    setConnected,
    setConnectionFailure,
    updateNeeded,
    version,
  };
});

const demoMode = import.meta.env.VITE_DEMO_MODE;

/**
 * In demo mode, simulate a release version for testing version-gated features.
 * setuptools-scm already bumps the patch in dev builds, so 'patch' just strips '.dev'.
 */
function applyDemoMode(version: string): string {
  if (demoMode === undefined)
    return version;

  const sanitized = version.replace('.dev', '');
  if (demoMode === 'minor') {
    const parts = sanitized.split('.');
    parts[1] = `${Number.parseInt(parts[1]) + 1}`;
    parts[2] = '0';
    return parts.join('.');
  }
  return sanitized;
}

function defaultVersion(): Version {
  return {
    downloadUrl: '',
    latestVersion: '',
    version: '',
  };
}

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useMainStore, import.meta.hot));
