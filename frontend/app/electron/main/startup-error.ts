import type { LogService } from '@electron/main/log-service';
import type { UnusableBinary } from '@shared/starling/binary-types';
import { IpcCommands } from '@electron/ipc-commands';
import { BackendCode, type StartupError } from '@shared/ipc';
import { type BrowserWindow, ipcMain } from 'electron';

/**
 * Holds the startup error and hands it to the renderer.
 *
 * @remarks
 * A backend failure can happen before there is a renderer to tell, so the error is kept here until
 * the renderer either announces itself over `RENDERER_READY` and gets it pushed, or pulls it
 * synchronously over `SYNC_GET_STARTUP_ERROR` while it initialises.
 */
export class StartupErrorChannel {
  private error: StartupError | null = null;
  private rendererReady: boolean = false;

  constructor(
    private readonly logger: LogService,
    private readonly window: () => BrowserWindow | null,
  ) {}

  /** Registers the synchronous pull and the readiness signal. One call per window. */
  listen(): void {
    ipcMain.on(IpcCommands.SYNC_GET_STARTUP_ERROR, (event) => {
      event.returnValue = this.error;
    });

    ipcMain.on(IpcCommands.RENDERER_READY, () => {
      this.rendererReady = true;
      this.push();
    });
  }

  /**
   * @remarks
   * A missing binary is never replaced by another error. One incident can report both, a crash
   * while the killed file is still on disk and then the file found gone, and a renderer that pulls
   * the error after a reload must still get the report that explains it. {@link StartupErrorChannel.clear}
   * lifts this when the backend is started again.
   */
  set(backendOutput: string | Error, code: BackendCode, unusableBinary?: UnusableBinary): void {
    if (this.error?.code === BackendCode.MISSING_BINARY && code !== BackendCode.MISSING_BINARY)
      return;

    const message = typeof backendOutput === 'string' ? backendOutput : backendOutput.message;
    this.error = { code, message, unusableBinary };

    if (this.rendererReady)
      this.push();
  }

  /** Forgets the held error, for a backend being started again. */
  clear(): void {
    this.error = null;
  }

  reset(): void {
    ipcMain.removeAllListeners(IpcCommands.SYNC_GET_STARTUP_ERROR);
    ipcMain.removeAllListeners(IpcCommands.RENDERER_READY);
    this.error = null;
    this.rendererReady = false;
  }

  private push(): void {
    const webContents = this.window()?.webContents;
    if (!this.error || !webContents)
      return;

    try {
      webContents.send(IpcCommands.STARTUP_ERROR, this.error);
    }
    catch (error) {
      this.logger.error('Failed to push startup error to renderer:', error);
    }
  }
}
