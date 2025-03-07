import type { App } from 'electron';
import fs from 'node:fs';
import path from 'node:path';

const ELECTRON_LOG_FILENAME = 'rotki_electron.log';

const CORE_LOG_FILENAME = 'rotkehlchen.log';

const COLIBRI_LOG_FILENAME = 'colibri.log';

const LOG_DIR = 'logs';

export class LogService {
  readonly defaultLogDirectory: string;
  private _logDirectory: string = this.getLogDirectory();

  private get logDirectory(): string {
    return this._logDirectory;
  }

  get electronLogPath(): string {
    return path.join(this.logDirectory, ELECTRON_LOG_FILENAME);
  }

  get coreProcessLogPath(): string {
    return path.join(this.logDirectory, CORE_LOG_FILENAME);
  }

  get colibriProcessLogFile(): string {
    return path.join(this.logDirectory, COLIBRI_LOG_FILENAME);
  }

  constructor(app: App) {
    app.setAppLogsPath(path.join(app.getPath('appData'), 'rotki', LOG_DIR));
    this.defaultLogDirectory = app.getPath('logs');
    this.updateLogDirectory();
  }

  private getLogDirectory(): string {
    if (import.meta.env.VITE_DEV_LOGS) {
      return path.join(import.meta.dirname, '..', '..', LOG_DIR);
    }
    else {
      return this.defaultLogDirectory;
    }
  }

  log(message: string | Error): void {
    if (!message)
      return;

    try {
      const timestamp = new Date(Date.now()).toISOString();
      const logMessage = `${timestamp}: ${message.toString()}`;
      fs.appendFileSync(this.electronLogPath, `${logMessage}\n`, { encoding: 'utf8' });
      if (message instanceof Error) {
        console.error(message);
      }
      else {
        // eslint-disable-next-line no-console
        console.log(logMessage);
      }
    }
    catch {
      // Not much we can do if an error happens here.
    }
  }

  updateLogDirectory(logDirectory: string = this.getLogDirectory()): void {
    if (logDirectory && !fs.existsSync(logDirectory))
      fs.mkdirSync(logDirectory);
    this._logDirectory = logDirectory;
  }
}
