import type { LogService } from '@electron/main/log-service';
import type { BackendOptions } from '@shared/ipc';
import { assert } from '@rotki/common';

interface BackendHandlersCallbacks {
  restartSubprocesses: (options: Partial<BackendOptions>) => Promise<void>;
  sendIpcMessage: (channel: string, ...args: any[]) => void;
}

export class BackendHandlers {
  private callbacks: BackendHandlersCallbacks | null = null;
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

  restartBackend = async (options: Partial<BackendOptions>): Promise<boolean> => {
    this.logger.info(`Restarting backend with options: ${JSON.stringify(options)}`);

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
