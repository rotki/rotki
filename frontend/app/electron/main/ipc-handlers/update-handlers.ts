import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import type { ProgressInfo } from 'electron-builder';
import { IpcCommands } from '@electron/ipc-commands';
import { startPromise } from '@shared/utils';
import electronUpdater from 'electron-updater';

const { autoUpdater } = electronUpdater;

interface UpdateHandlersCallbacks {
  terminateSubprocesses: (update?: boolean) => Promise<void>;
  updateDownloadProgress: (progress: number) => void;
}

export class UpdateHandlers {
  private callbacks: UpdateHandlersCallbacks | null = null;
  private static readonly updateTimeout = 5000;

  constructor(
    private readonly logger: LogService,
    private readonly config: AppConfig,
  ) {
    this.setupAutoUpdater();
  }

  initialize(callbacks: UpdateHandlersCallbacks): void {
    this.callbacks = callbacks;
  }

  private get requireCallbacks(): UpdateHandlersCallbacks {
    const callbacks = this.callbacks;
    if (!callbacks) {
      throw new Error('UpdateHandlers callbacks not initialized');
    }
    return callbacks;
  }

  private setupAutoUpdater(): void {
    autoUpdater.autoDownload = false;
    autoUpdater.logger = {
      error: (message?: any) => this.logger.error(message),
      info: (message?: any) => this.logger.info(message),
      debug: (message: string) => this.logger.debug(message),
      warn: (message?: any) => this.logger.warn(message),
    };
  }

  checkForUpdates = async (): Promise<boolean> => {
    if (this.config.isDev) {
      console.warn('Running in development skipping auto-updater check');
      return false;
    }

    return new Promise<boolean>((resolve) => {
      autoUpdater.once('update-available', () => resolve(true));
      autoUpdater.once('update-not-available', () => resolve(false));
      autoUpdater.once('error', (error: Error) => {
        this.logger.error(error);
        resolve(false);
      });

      autoUpdater.checkForUpdates().catch((error: any) => {
        this.logger.error(error);
        resolve(false);
      });
    });
  };

  downloadUpdate = async (event: Electron.IpcMainInvokeEvent): Promise<boolean> => {
    const progress = (progress: ProgressInfo) => {
      event.sender.send(IpcCommands.DOWNLOAD_PROGRESS, progress.percent);
      this.requireCallbacks.updateDownloadProgress(progress.percent);
    };

    return new Promise<boolean>((resolve) => {
      autoUpdater.on('download-progress', progress);
      autoUpdater.downloadUpdate()
        .then(() => resolve(true))
        .catch((error) => {
          this.logger.error(error);
          resolve(false);
        })
        .finally(() => {
          autoUpdater.removeListener('download-progress', progress);
        });
    });
  };

  installUpdate = async (): Promise<Error | boolean> => {
    const quit = new Promise<void>((resolve, reject) => setTimeout(() => {
      startPromise((async () => {
        try {
          await this.quitAndInstallUpdates();
          resolve();
        }
        catch (error: any) {
          this.logger.error(error);
          reject(error instanceof Error ? error : new Error(error));
        }
      })());
    }, UpdateHandlers.updateTimeout));

    try {
      await quit;
      return true;
    }
    catch (error: any) {
      this.logger.error(error);
      return error;
    }
  };

  private async quitAndInstallUpdates(): Promise<void> {
    await this.requireCallbacks.terminateSubprocesses(true);
    autoUpdater.quitAndInstall();
  }
}
