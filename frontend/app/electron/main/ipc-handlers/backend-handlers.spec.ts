import type { LogService } from '@electron/main/log-service';
import type { BackendOptions } from '@shared/ipc';
import { IpcCommands } from '@electron/ipc-commands';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { BackendHandlers } from './backend-handlers';

describe('backendHandlers', () => {
  let handlers: BackendHandlers;
  let restartSubprocesses: Mock<(options: Partial<BackendOptions>) => Promise<void>>;
  let getRunningCorePIDs: Mock<() => Promise<number[]>>;
  let sendIpcMessage: Mock<(channel: string, ...args: any[]) => void>;
  let coreRunning: boolean;

  const options: Partial<BackendOptions> = { dataDirectory: '/tmp/rotki-data' };

  beforeEach(() => {
    coreRunning = false;
    restartSubprocesses = vi.fn<(options: Partial<BackendOptions>) => Promise<void>>().mockResolvedValue(undefined);
    getRunningCorePIDs = vi.fn<() => Promise<number[]>>().mockResolvedValue([]);
    sendIpcMessage = vi.fn<(channel: string, ...args: any[]) => void>();

    handlers = new BackendHandlers(createMock<LogService>());
    handlers.initialize({
      restartSubprocesses,
      getRunningCorePIDs,
      isCoreRunning: () => coreRunning,
      sendIpcMessage,
    });
  });

  it('should start the backend on first load when none is running', async () => {
    coreRunning = false;

    const success = await handlers.restartBackend(options);

    expect(success).toBe(true);
    expect(restartSubprocesses).toHaveBeenCalledWith(options);
  });

  it('should attach instead of restarting when a backend is already running (refresh)', async () => {
    // first call performs the initial start
    await handlers.restartBackend(options);
    restartSubprocesses.mockClear();
    coreRunning = true;

    // second call simulates a page refresh: not forced, backend already up
    const success = await handlers.restartBackend(options);

    expect(success).toBe(true);
    expect(restartSubprocesses).not.toHaveBeenCalled();
  });

  it('should restart a running backend when forceRestart is true', async () => {
    await handlers.restartBackend(options);
    restartSubprocesses.mockClear();
    coreRunning = true;

    const success = await handlers.restartBackend(options, true);

    expect(success).toBe(true);
    expect(restartSubprocesses).toHaveBeenCalledWith(options);
  });

  it('should detect and report an existing backend process only on first start', async () => {
    getRunningCorePIDs.mockResolvedValue([4242]);
    const send = vi.fn<Electron.WebContents['send']>();
    const event = createMock<Electron.IpcMainInvokeEvent>({ sender: { send } });

    await handlers.restartBackend(options, false, event);
    expect(getRunningCorePIDs).toHaveBeenCalledTimes(1);
    expect(send).toHaveBeenCalledWith(IpcCommands.BACKEND_PROCESS_DETECTED, [4242]);

    // subsequent calls must not re-run PID detection
    await handlers.restartBackend(options, false, event);
    expect(getRunningCorePIDs).toHaveBeenCalledTimes(1);
  });
});
