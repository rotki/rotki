import type { LogService } from '@electron/main/log-service';
import type { BackendCode, StartupError } from '@shared/ipc';
import { IpcCommands } from '@electron/ipc-commands';
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

  set(backendOutput: string | Error, code: BackendCode): void {
    const message = typeof backendOutput === 'string' ? backendOutput : backendOutput.message;
    this.error = { message, code };

    if (this.rendererReady)
      this.push();
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
