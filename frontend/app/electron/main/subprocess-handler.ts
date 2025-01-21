import * as os from 'node:os';
import process from 'node:process';
import { app } from 'electron';
import { psList } from '@electron/main/ps-list';
import { getPortAndUrl } from '@electron/main/port-utils';
import { BackendCode, type BackendOptions } from '@shared/ipc';
import { ProcessManager } from '@electron/main/process-manager';
import { ColibriConfig } from '@electron/main/colibri-args';
import { RotkiCoreConfig } from '@electron/main/core-args';
import type { LogService } from '@electron/main/log-service';
import type { AppConfig } from '@electron/main/app-config';

interface SubprocessHandlerErrorListener {
  onProcessError: (message: string | Error, code: BackendCode) => void;
}

export class SubprocessHandler {
  private exiting: boolean;

  private readonly colibriManager: ProcessManager;
  private readonly coreManager: ProcessManager;

  constructor(private readonly logger: LogService, private readonly config: AppConfig) {
    this.exiting = false;
    const startupMessage = `
    ------------------
    | Starting rotki |
    ------------------`;
    this.logger.log(startupMessage);

    this.colibriManager = new ProcessManager(
      'colibri',
      msg => this.logger.log(msg),
    );
    this.coreManager = new ProcessManager(
      'rotki-core',
      msg => this.logger.log(msg),
      { useWindowsTermination: true },
    );
  }

  async checkForBackendProcess(): Promise<number[]> {
    try {
      this.logger.log('Checking for running rotki-core processes');
      const runningProcesses = await psList({ all: true });
      const matches = runningProcesses.filter(
        process => process.cmd?.includes('-m rotkehlchen') || process.cmd?.includes('rotki-core'),
      );
      return matches.map(p => p.pid);
    }
    catch (error: any) {
      this.logger.log(error.toString());
      return [];
    }
  }

  private checkIfMacOsVersionIsSupported(): boolean {
    if (os.platform() !== 'darwin') {
      return true;
    }

    const releaseVersionParts = os.release().split('.');
    const majorVersion = Number.parseInt(releaseVersionParts[0]);
    return !(releaseVersionParts.length > 0 && majorVersion < 17);
  }

  private checkIfWindowsVersionIsSupported(): boolean {
    if (os.platform() !== 'win32') {
      return true;
    }
    const releaseVersionParts = os.release().split('.');

    if (releaseVersionParts.length > 1) {
      const majorVersion = Number.parseInt(releaseVersionParts[0]);
      const minorVersion = Number.parseInt(releaseVersionParts[1]);

      // Win 7 (v6.1) or earlier
      const windowsVersion = majorVersion + minorVersion * 0.1;
      return windowsVersion >= 6.1;
    }
    return true;
  }

  async startProcesses(options: Partial<BackendOptions>, listener: SubprocessHandlerErrorListener): Promise<void> {
    this.logger.log('Preparing to start processes');
    this.logger.updateLogDirectory(options.logDirectory);

    if (process.env.SKIP_PYTHON_BACKEND) {
      this.logger.log('Skipped starting rotki-core');
      return;
    }

    if (!this.checkIfMacOsVersionIsSupported()) {
      listener.onProcessError('rotki requires at least macOS High Sierra', BackendCode.MACOS_VERSION);
      return;
    }

    if (!this.checkIfWindowsVersionIsSupported()) {
      listener.onProcessError('rotki requires at least Windows 10', BackendCode.WIN_VERSION);
      return;
    }

    await this.startColibri();
    await this.startCore(options, listener);
  }

  private async startColibri() {
    this.logger.log('Preparing to start colibri');
    const [port, url, isNonDefault] = await getPortAndUrl(
      this.config.ports.colibriPort,
      this.config.urls.colibriApiUrl,
    );

    if (isNonDefault) {
      this.logger.log(`Using non-default port ${port} for colibri at ${url}`);
      this.config.urls.colibriApiUrl = url;
    }

    const { command, args, workDir } = ColibriConfig.create(this.config.isDev)
      .withLogfilePath(this.logger.colibriProcessLogFile)
      .withPort(port)
      .build();

    this.colibriManager.onExit((code) => {
      this.logger.log(`colibri exited with code: ${code}`);
    });
    this.colibriManager.onError((error) => {
      this.logger.log(`colibri exited with error: ${error}`);
    });
    this.colibriManager.start(command, args, workDir);
  }

  private async startCore(options: Partial<BackendOptions>, listener: SubprocessHandlerErrorListener) {
    this.logger.log('Preparing to start rotki-core');
    const [port, url, isNonDefault] = await getPortAndUrl(
      this.config.ports.corePort,
      this.config.urls.coreApiUrl,
    );

    if (isNonDefault) {
      this.logger.log(`Using non-default port ${port} for rotki-core at ${url}`);
      this.config.urls.coreApiUrl = url;
    }

    const { command, args, workDir } = RotkiCoreConfig.create(this.config.isDev, options)
      .withLogFile(this.logger.coreProcessLogPath)
      .withPort(port)
      .build();

    this.coreManager.onExit((code, signal, lastError) => {
      this.logger.log(`rotki-core exited with signal: ${signal} (Code: ${code})`);
      /**
       * On win32 we can also get a null code on SIGTERM
       */
      if (!(code === 0 || code === null)) {
        // Notify the main window every 2 seconds until it acks the notification
        listener.onProcessError(lastError, BackendCode.TERMINATED);
      }
    });

    this.coreManager.onError((error) => {
      this.logger.log(`Encountered an error while trying to start rotki-core\n\n${error.toString()}`);
      listener.onProcessError(error, BackendCode.TERMINATED);
    });

    this.coreManager.start(command, args, workDir);
  }

  async terminateProcesses(restart: boolean = false): Promise<void> {
    if (this.exiting)
      return;

    this.exiting = true;
    await this.colibriManager?.terminate();
    await this.coreManager?.terminate();
    this.exiting = false;

    if (!restart)
      app.quit();
  }
}
