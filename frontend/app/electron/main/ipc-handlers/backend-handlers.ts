import type { LogService } from '@electron/main/log-service';
import type { BackendOptions } from '@shared/ipc';
import { IpcCommands } from '@electron/ipc-commands';
import { assert } from '@rotki/common';

interface BackendHandlersCallbacks {
  restartSubprocesses: (options: Partial<BackendOptions>) => Promise<void>;
  getRunningCorePIDs: () => Promise<number[]>;
  sendIpcMessage: (channel: string, ...args: any[]) => void;
}

export class BackendHandlers {
  private callbacks: BackendHandlersCallbacks | null = null;
  private firstStart = true;
  private restarting = false;

  private get requireCallbacks(): BackendHandlersCallbacks {
    const callbacks = this.callbacks;
    assert(callbacks);
    return callbacks;
  }

  constructor(private readonly logger: LogService) {}

  initialize(callbacks: BackendHandlersCallbacks): void {
    this.callbacks = callbacks;
  }

  restartBackend = async (options: Partial<BackendOptions>, event?: Electron.IpcMainInvokeEvent): Promise<boolean> => {
    this.logger.info(`Restarting backend with options: ${JSON.stringify(options)}`);

    if (this.firstStart) {
      this.firstStart = false;
      const pids = await this.requireCallbacks.getRunningCorePIDs();
      if (pids.length > 0) {
        if (event) {
          event.sender.send(IpcCommands.BACKEND_PROCESS_DETECTED, pids);
        }
        this.logger.warn(`Detected existing backend process: ${pids.join(', ')}`);
      }
      else {
        this.logger.debug('No existing backend process detected');
      }
    }

    let success = false;

    if (!this.restarting) {
      this.restarting = true;
      try {
        this.logger.info('Starting backend process');
        await this.requireCallbacks.restartSubprocesses(options);
        success = true;
      }
      catch (error: any) {
        this.logger.error(error);
      }
      finally {
        this.restarting = false;
      }
    }

    return success;
  };
}
