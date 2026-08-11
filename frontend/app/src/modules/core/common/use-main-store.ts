import type { LogLevel } from '@shared/log-level';
import type { Version } from '@/modules/core/common/action';
import type { DefaultBackendArguments } from '@/modules/shell/app/backend';
import { checkIfDevelopment } from '@shared/utils';
import { getDefaultLogLevel } from '@/modules/core/common/logging/logging';

export const useMainStore = defineStore('main', () => {
  const version = ref<Version>(defaultVersion());
  const connected = ref<boolean>(false);
  const connectionFailure = ref<boolean>(false);
  const connectionEnabled = ref<boolean>(true);
  const dataDirectory = ref<string>('');
  const logLevel = ref<LogLevel>(getDefaultLogLevel());
  // Whether the operator acknowledged that the API is reachable without authentication.
  const unauthenticatedApiAccepted = ref<boolean>(true);
  // Whether the backend runs behind session-cookie auth (docker with ROTKI_SESSION_KEY).
  const sessionAuthEnabled = ref<boolean>(false);
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
    isDevelop,
    logLevel,
    sessionAuthEnabled,
    setConnected,
    setConnectionFailure,
    unauthenticatedApiAccepted,
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

/**
 * Until the backend answers, the frontend build version is the closest thing we have.
 * It keeps the about dialog and the release notes link sane on the login screen,
 * and gets overwritten by the backend version as soon as the connection is up.
 */
function defaultVersion(): Version {
  return {
    downloadUrl: '',
    latestVersion: '',
    version: __APP_VERSION__,
  };
}

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useMainStore, import.meta.hot));
