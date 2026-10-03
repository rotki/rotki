import type { LogService } from '@electron/main/log-service';
import type { BrowserWindow } from 'electron';
import { IpcCommands } from '@electron/ipc-commands';
import { BackendCode, type StartupError } from '@shared/ipc';
import { QUARANTINED_COLIBRI } from '@test/fixtures/unusable-binary';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { StartupErrorChannel } from './startup-error';

type Send = (channel: string, ...args: any[]) => void;

const { onMock, removeAllListenersMock } = vi.hoisted(() => ({
  onMock: vi.fn<(channel: string, listener: (...args: any[]) => void) => void>(),
  removeAllListenersMock: vi.fn<(channel: string) => void>(),
}));

vi.mock('electron', () => ({
  ipcMain: { on: onMock, removeAllListeners: removeAllListenersMock },
}));

describe('startupErrorChannel', () => {
  let send: Mock<Send>;
  let window: BrowserWindow | null;
  let channel: StartupErrorChannel;

  /** The `SYNC_GET_STARTUP_ERROR` reply, which the renderer reads off `event.returnValue`. */
  function pull(): StartupError | null {
    const handler = onMock.mock.calls.find(([channel]) => channel === IpcCommands.SYNC_GET_STARTUP_ERROR)?.[1];
    const event = { returnValue: undefined };
    handler?.(event);
    return event.returnValue ?? null;
  }

  function signalRendererReady(): void {
    const handler = onMock.mock.calls.find(([channel]) => channel === IpcCommands.RENDERER_READY)?.[1];
    handler?.();
  }

  beforeEach(() => {
    vi.clearAllMocks();
    send = vi.fn<Send>();
    window = createMock<BrowserWindow>({ webContents: createMock<BrowserWindow['webContents']>({ send }) });
    channel = new StartupErrorChannel(createMock<LogService>(), () => window);
    channel.listen();
  });

  it('should hold an error raised before the renderer is ready, and answer the pull with it', () => {
    channel.set('backend is gone', BackendCode.TERMINATED);

    expect(send).not.toHaveBeenCalled();
    expect(pull()).toEqual({ code: BackendCode.TERMINATED, message: 'backend is gone' });
  });

  it('should push the held error once the renderer announces itself', () => {
    channel.set('backend is gone', BackendCode.TERMINATED);
    signalRendererReady();

    expect(send).toHaveBeenCalledWith(IpcCommands.STARTUP_ERROR, {
      code: BackendCode.TERMINATED,
      message: 'backend is gone',
    });
  });

  it('should push immediately when the renderer is already ready', () => {
    signalRendererReady();
    channel.set('backend is gone', BackendCode.TERMINATED);

    expect(send).toHaveBeenCalledWith(IpcCommands.STARTUP_ERROR, {
      code: BackendCode.TERMINATED,
      message: 'backend is gone',
    });
  });

  it('should push nothing when the renderer signals ready and no error was raised', () => {
    signalRendererReady();

    expect(send).not.toHaveBeenCalled();
  });

  it('should flatten an Error to its message', () => {
    signalRendererReady();
    channel.set(new Error('spawn ENOENT'), BackendCode.TERMINATED);

    expect(send).toHaveBeenCalledWith(IpcCommands.STARTUP_ERROR, {
      code: BackendCode.TERMINATED,
      message: 'spawn ENOENT',
    });
  });

  it('should carry the unusable binary alongside the message', () => {
    signalRendererReady();
    channel.set('colibri is gone', BackendCode.MISSING_BINARY, QUARANTINED_COLIBRI);

    expect(send).toHaveBeenCalledWith(IpcCommands.STARTUP_ERROR, {
      code: BackendCode.MISSING_BINARY,
      message: 'colibri is gone',
      unusableBinary: QUARANTINED_COLIBRI,
    });
  });

  it('should keep a missing binary report when a generic error follows it, for a renderer that pulls later', () => {
    signalRendererReady();
    channel.set('colibri is gone', BackendCode.MISSING_BINARY, QUARANTINED_COLIBRI);
    send.mockClear();

    channel.set('The rotki backend stopped unexpectedly.', BackendCode.TERMINATED);

    expect(send).not.toHaveBeenCalled();
    expect(pull()).toEqual({ code: BackendCode.MISSING_BINARY, message: 'colibri is gone', unusableBinary: QUARANTINED_COLIBRI });
  });

  it('should take a generic error again once cleared for a restart', () => {
    channel.set('colibri is gone', BackendCode.MISSING_BINARY, QUARANTINED_COLIBRI);

    channel.clear();
    expect(pull()).toBeNull();

    channel.set('backend is gone', BackendCode.TERMINATED);
    expect(pull()).toEqual({ code: BackendCode.TERMINATED, message: 'backend is gone' });
  });

  it('should survive a window that is already gone', () => {
    signalRendererReady();
    window = null;

    expect(() => channel.set('backend is gone', BackendCode.TERMINATED)).not.toThrow();
    expect(pull()).toEqual({ code: BackendCode.TERMINATED, message: 'backend is gone' });
  });

  it('should drop the error and the readiness on reset', () => {
    signalRendererReady();
    channel.set('backend is gone', BackendCode.TERMINATED);
    channel.reset();

    expect(removeAllListenersMock).toHaveBeenCalledWith(IpcCommands.SYNC_GET_STARTUP_ERROR);
    expect(removeAllListenersMock).toHaveBeenCalledWith(IpcCommands.RENDERER_READY);
    expect(pull()).toBeNull();

    send.mockClear();
    channel.set('a later failure', BackendCode.TERMINATED);
    expect(send).not.toHaveBeenCalled();
  });
});
