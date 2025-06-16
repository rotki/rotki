import type { App } from 'electron';
import fs from 'node:fs';
import path from 'node:path';
import * as util from 'node:util';
import { LogManager } from '@electron/main/log-manager';
import { type LogRotationConfig, RotationTiming } from '@electron/main/log-rotation-config';
import { LogLevel } from '@shared/log-level';

const ELECTRON_LOG_FILENAME = 'rotki_electron.log';
const CORE_LOG_FILENAME = 'rotkehlchen.log';
const COLIBRI_LOG_FILENAME = 'colibri.log';
const LOG_DIR = 'logs';

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
    return level >= this.currentLogLevel;
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
  private writeLog(level: LogLevel, logFilePath: string = this.electronLogPath, ...args: any[]): void {
    if (!this.shouldLog(level) || args.length === 0) {
      return;
    }

    try {
      this.logManager.incrementWriteCount();
      this.logManager.checkRotation();

      const timestamp = new Date(Date.now()).toISOString();
      const levelString = this.getLogLevelString(level);
      const message = this.formatMessage(...args);
      const logMessage = `${timestamp} [${levelString}]: ${message}`;

      fs.appendFileSync(logFilePath, `${logMessage}\n`, { encoding: 'utf8' });

      this.outputToConsole(level, logMessage);
    }
    catch {
      // Not much we can do if an error happens here.
    }
  }

  /**
   * Log debug message with printf-style formatting
   */
  debug(message?: any, ...optionalParams: any[]): void {
    this.writeLog(LogLevel.DEBUG, this.electronLogPath, message, ...optionalParams);
  }

  /**
   * Log info message with printf-style formatting
   */
  info(message?: any, ...optionalParams: any[]): void {
    this.writeLog(LogLevel.INFO, this.electronLogPath, message, ...optionalParams);
  }

  /**
   * Log warning message with printf-style formatting
   */
  warn(message?: any, ...optionalParams: any[]): void {
    this.writeLog(LogLevel.WARNING, this.electronLogPath, message, ...optionalParams);
  }

  /**
   * Log error message with printf-style formatting
   */
  error(message?: any, ...optionalParams: any[]): void {
    this.writeLog(LogLevel.ERROR, this.electronLogPath, message, ...optionalParams);
  }

  write(level: LogLevel, message?: any, ...optionalParams: any[]): void {
    this.writeLog(level, this.electronLogPath, message, ...optionalParams);
  }

  updateLogDirectory(logDirectory: string = this.getLogDirectory()): void {
    if (logDirectory && !fs.existsSync(logDirectory))
      fs.mkdirSync(logDirectory);
    this._logDirectory = logDirectory;
    this.logManager.updateLogDirectory(logDirectory);
  }
}
