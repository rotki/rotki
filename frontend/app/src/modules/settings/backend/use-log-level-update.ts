import type { LogLevel } from '@shared/log-level';
import { setLevel } from '@/modules/core/common/logging/logging';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

interface UseLogLevelUpdateReturn {
  applyLogLevelChange: (level: LogLevel) => Promise<void>;
}

/**
 * Propagates a log level change to every consumer that tracks it at runtime:
 * the Python backend (REST), Colibri (REST), the frontend consola logger,
 * and the Electron main-process LogService (IPC). Used by both the
 * onboarding and in-app settings screens so the chain stays in sync.
 */
export function useLogLevelUpdate(): UseLogLevelUpdateReturn {
  const { updateBackendConfiguration, updateColibriConfiguration } = useSettingsApi();
  const interop = useInterop();

  async function applyLogLevelChange(level: LogLevel): Promise<void> {
    await updateBackendConfiguration(level);
    await updateColibriConfiguration(level);
    setLevel(level);
    if (interop.isPackaged) {
      interop.setLogLevel(level);
    }
  }

  return { applyLogLevelChange };
}
