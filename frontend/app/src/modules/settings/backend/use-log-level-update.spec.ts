import { LogLevel } from '@shared/log-level';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLogLevelUpdate } from '@/modules/settings/backend/use-log-level-update';

const { setLevelMock, setLogLevelMock, updateBackendConfigurationMock, updateColibriConfigurationMock } = vi.hoisted(() => ({
  setLevelMock: vi.fn(),
  setLogLevelMock: vi.fn(),
  updateBackendConfigurationMock: vi.fn(),
  updateColibriConfigurationMock: vi.fn(),
}));

vi.mock('@/modules/core/common/logging/logging', async (): Promise<Record<string, unknown>> => {
  const mod = await vi.importActual<typeof import('@/modules/core/common/logging/logging')>('@/modules/core/common/logging/logging');
  return { ...mod, setLevel: setLevelMock };
});

vi.mock('@/modules/shell/app/use-electron-interop', (): Record<string, unknown> => ({
  useInterop: vi.fn().mockReturnValue({
    isPackaged: true,
    setLogLevel: setLogLevelMock,
  }),
}));

vi.mock('@/modules/settings/api/use-settings-api', (): Record<string, unknown> => ({
  useSettingsApi: vi.fn().mockReturnValue({
    updateBackendConfiguration: updateBackendConfigurationMock,
    updateColibriConfiguration: updateColibriConfigurationMock,
  }),
}));

describe('useLogLevelUpdate', () => {
  beforeEach((): void => {
    setLevelMock.mockClear();
    setLogLevelMock.mockClear();
    updateBackendConfigurationMock.mockReset();
    updateBackendConfigurationMock.mockResolvedValue({});
    updateColibriConfigurationMock.mockReset();
    updateColibriConfigurationMock.mockResolvedValue({});
  });

  it('should propagate the level to backend, colibri, consola and the Electron LogService', async () => {
    const { applyLogLevelChange } = useLogLevelUpdate();
    await applyLogLevelChange(LogLevel.WARNING);

    expect(updateBackendConfigurationMock).toHaveBeenCalledWith('warning');
    expect(updateColibriConfigurationMock).toHaveBeenCalledWith('warning');
    expect(setLevelMock).toHaveBeenCalledWith('warning');
    expect(setLogLevelMock).toHaveBeenCalledWith('warning');
  });

  it('should update the backend before colibri so a remote failure does not leave the two services split', async () => {
    const order: string[] = [];
    updateBackendConfigurationMock.mockImplementation(async () => {
      order.push('backend');
    });
    updateColibriConfigurationMock.mockImplementation(async () => {
      order.push('colibri');
    });

    const { applyLogLevelChange } = useLogLevelUpdate();
    await applyLogLevelChange(LogLevel.DEBUG);

    expect(order).toStrictEqual(['backend', 'colibri']);
  });

  it('should skip the Electron LogService IPC when not running in a packaged build', async () => {
    const { useInterop } = await import('@/modules/shell/app/use-electron-interop');
    vi.mocked(useInterop).mockReturnValueOnce(createMock<ReturnType<typeof useInterop>>({
      isPackaged: false,
      setLogLevel: setLogLevelMock,
    }));

    const { applyLogLevelChange } = useLogLevelUpdate();
    await applyLogLevelChange(LogLevel.INFO);

    expect(setLevelMock).toHaveBeenCalledWith('info');
    expect(setLogLevelMock).not.toHaveBeenCalled();
  });
});
