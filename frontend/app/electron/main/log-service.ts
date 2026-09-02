import type { App } from 'electron';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import * as util from 'node:util';
import { isLogLevelActive } from '@electron/main/log-level-severity';
import { LogManager } from '@electron/main/log-manager';
import { type LogRotationConfig, RotationTiming } from '@electron/main/log-rotation-config';
import { LogLevel } from '@shared/log-level';

const ELECTRON_LOG_FILENAME = 'rotki_electron.log';
const CORE_LOG_FILENAME = 'rotkehlchen.log';
const COLIBRI_LOG_FILENAME = 'colibri.log';
const LOG_DIR = 'logs';

// ANSI colors for the level badge on the console. The file stays plain so it
// remains greppable; honor NO_COLOR for redirected/piped output.
const ANSI_RESET = '\u001B[0m';
const LEVEL_COLORS: Record<LogLevel, string> = {
  [LogLevel.CRITICAL]: '\u001B[1;31m', // bold red
  [LogLevel.ERROR]: '\u001B[31m', // red
  [LogLevel.WARNING]: '\u001B[33m', // yellow
  [LogLevel.INFO]: '\u001B[32m', // green
  [LogLevel.DEBUG]: '\u001B[36m', // cyan
  [LogLevel.TRACE]: '\u001B[90m', // gray
};
// Colors for the source marker ([main]/[vue]/[starling]) on the console.
const SOURCE_COLORS: Record<string, string> = {
  '[main]': '\u001B[35m', // magenta
  '[vue]': '\u001B[34m', // blue
  '[starling]': '\u001B[95m', // bright magenta
};
const USE_COLOR = !process.env.NO_COLOR;

/**
 * Colorize a known leading source marker (": [main] ...", ": [vue] ...", etc.)
 * for the console. Unknown/absent markers are returned untouched.
 */
function colorizeSource(rest: string): string {
  for (const [tag, color] of Object.entries(SOURCE_COLORS)) {
    const prefix = `: ${tag}`;
    if (rest.startsWith(prefix))
      return `: ${color}${tag}${ANSI_RESET}${rest.slice(prefix.length)}`;
  }
  return rest;
}

export class LogService {
  readonly defaultLogDirectory: string;
  private _logDirectory: string = this.getLogDirectory();
  private readonly logManager: LogManager;
  private currentLogLevel: LogLevel = LogLevel.INFO;
  private rotationConfig: LogRotationConfig = {
    maxFiles: 5,
    maxFileSize: 5 * 1024 * 1024,
    compressRotated: true,
    timing: RotationTiming.HYBRID,
    writeCountThreshold: 100,
    checkInterval: 60_000,
  };

  /**
   * The directory logs are actually written to. Follows `LOGDIR` and so can differ
   * from {@link defaultLogDirectory} — anything pointing a user at their logs must
   * read this, not the platform default.
   */
  get logDirectory(): string {
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
    this.logManager = new LogManager(this.logDirectory, ELECTRON_LOG_FILENAME, this.rotationConfig);
    this.updateLogDirectory();
    this.logManager.initializeRotationTimer();
  }

  private getLogDirectory(): string {
    if (import.meta.env.VITE_DEV_LOGS) {
      return path.join(import.meta.dirname, '..', '..', LOG_DIR);
    }
    else {
      return this.defaultLogDirectory;
    }
  }

  /**
   * Set the minimum log level
   * @param level
   */
  setLogLevel(level: LogLevel): void {
    this.currentLogLevel = level;
  }

  /**
   * Get the current log level
   */
  getLogLevel(): LogLevel {
    return this.currentLogLevel;
  }

  /**
   * Configure log rotation settings
   */
  setRotationConfig(config: Partial<LogRotationConfig>): void {
    const oldTiming = this.rotationConfig.timing;
    this.rotationConfig = { ...this.rotationConfig, ...config };
    this.logManager.updateRotationConfig(this.rotationConfig);

    if (oldTiming !== this.rotationConfig.timing) {
      this.logManager.stopRotationTimer();
      this.logManager.initializeRotationTimer();
    }
  }

  /**
   * Check if a log level should be written based on the current log level
   */
  private shouldLog(level: LogLevel): boolean {
    return isLogLevelActive(level, this.currentLogLevel);
  }

  private getLogLevelString(level: LogLevel): string {
    return level.toUpperCase();
  }

  /**
   * Format the log message with arguments (similar to console.log behavior)
   */
  private formatMessage(...args: any[]): string {
    if (args.length === 0)
      return '';

    if (typeof args[0] === 'string' && args.length > 1) {
      return util.format(...args);
    }

    return args.map((arg) => {
      if (arg instanceof Error) {
        return `${arg.message}\n${arg.stack}`;
      }
      if (typeof arg === 'object') {
        try {
          return JSON.stringify(arg, null, 2);
        }
        catch {
          return String(arg);
        }
      }
      return String(arg);
    }).join(' ');
  }

  private outputToConsole(level: LogLevel, logMessage: string): void {
    /* eslint-disable no-console */
    const consoleMethodMap = new Map<LogLevel, (message: string) => void>([
      [LogLevel.DEBUG, console.debug],
      [LogLevel.INFO, console.log],
      [LogLevel.WARNING, console.warn],
      [LogLevel.ERROR, console.error],
      [LogLevel.CRITICAL, console.error],
      [LogLevel.TRACE, console.debug],
    ]);

    const consoleMethod = consoleMethodMap.get(level) ?? console.log;
    /* eslint-enable no-console */
    consoleMethod(logMessage);
  }

  /**
   * Core logging method
   */
  private writeLog(level: LogLevel, source: 'main' | 'forwarded', ...args: any[]): void {
    if (!this.shouldLog(level) || args.length === 0) {
      return;
    }

    try {
      this.logManager.incrementWriteCount();
      this.logManager.checkRotation();

      const timestamp = new Date(Date.now()).toISOString();
      const levelString = this.getLogLevelString(level);
      const message = this.formatMessage(...args);
      // Tag logs that originate in the electron main process. Forwarded logs
      // (renderer, starling) already carry their own source marker ([vue], [starling]).
      const sourceTag = source === 'main' ? '[main] ' : '';
      const rest = `: ${sourceTag}${message}`;

      // The file keeps the full ISO timestamp and plain markers for later reading;
      // stdout skips the timestamp (the terminal already shows time) and colors the
      // level badge and source marker for readability.
      fs.appendFileSync(this.electronLogPath, `${timestamp} [${levelString}]${rest}\n`, { encoding: 'utf8' });

      if (USE_COLOR) {
        const badge = `${LEVEL_COLORS[level]}[${levelString}]${ANSI_RESET}`;
        this.outputToConsole(level, `${badge}${colorizeSource(rest)}`);
      }
      else {
        this.outputToConsole(level, `[${levelString}]${rest}`);
      }
    }
    catch {
      // Not much we can do if an error happens here.
    }
  }

  /**
   * Log debug message with printf-style formatting
   */
  debug(message?: any, ...optionalParams: any[]): void {
    this.writeLog(LogLevel.DEBUG, 'main', message, ...optionalParams);
  }

  /**
   * Log info message with printf-style formatting
   */
  info(message?: any, ...optionalParams: any[]): void {
    this.writeLog(LogLevel.INFO, 'main', message, ...optionalParams);
  }

  /**
   * Log warning message with printf-style formatting
   */
  warn(message?: any, ...optionalParams: any[]): void {
    this.writeLog(LogLevel.WARNING, 'main', message, ...optionalParams);
  }

  /**
   * Log error message with printf-style formatting
   */
  error(message?: any, ...optionalParams: any[]): void {
    this.writeLog(LogLevel.ERROR, 'main', message, ...optionalParams);
  }

  write(level: LogLevel, message?: any, ...optionalParams: any[]): void {
    this.writeLog(level, 'forwarded', message, ...optionalParams);
  }

  updateLogDirectory(logDirectory: string = this.getLogDirectory()): void {
    if (logDirectory && !fs.existsSync(logDirectory))
      fs.mkdirSync(logDirectory);
    this._logDirectory = logDirectory;
    this.logManager.updateLogDirectory(logDirectory);
  }
}
