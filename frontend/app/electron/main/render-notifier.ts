import { ipcMain } from 'electron';
import type { BackendCode } from '@shared/ipc';

export class RenderNotifier {
  private notificationInterval?: number;

  constructor(private readonly logger: { log: (msg: string | Error) => void }) {
  }

  listenForAckMessages() {
    // Listen for ack messages from renderer process
    ipcMain.on('ack', (event, ...args) => {
      if (args[0] === 1)
        this.clearPending();
      else
        this.logger.log(`Warning: unknown ack code ${args[0]}`);
    });
  }

  clearPending() {
    if (this.notificationInterval)
      clearInterval(this.notificationInterval);
  }

  notify(
    window: Electron.BrowserWindow | null,
    backendOutput: string | Error,
    code: BackendCode,
  ): void {
    this.clearPending();
    // Notify the main window every 2 seconds until it acks the notification
    this.notificationInterval = setInterval(() => {
      /**
             * There is a possibility that the window has been already disposed and this
             * will result in an exception. In that case, we just catch and clear the notifier
             */
      try {
        window?.webContents.send('failed', backendOutput, code);
      }
      catch {
        clearInterval(this.notificationInterval);
      }
    }, 2000) as unknown as number;
  }
}
