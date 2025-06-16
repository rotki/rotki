import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { type LogRotationConfig, RotationTiming } from '@electron/main/log-rotation-config';
import { startPromise } from '@shared/utils';

export class LogManager {
  private isRotating: boolean = false;
  private lastRotationCheck: number = 0;
  private writeCount: number = 0;
  private rotationTimer: NodeJS.Timeout | null = null;

  constructor(
    private logDirectory: string,
    private readonly logFile: string,
    private rotationConfig: LogRotationConfig,
  ) {

  }

  private get logFilePath(): string {
    return path.join(this.logDirectory, this.logFile);
  }

  /**
   * Determine if a rotation check should happen based on timing strategy
   */
  private shouldCheckRotation(): boolean {
    switch (this.rotationConfig.timing) {
      case RotationTiming.BEFORE_WRITE:
        return true; // Always check

      case RotationTiming.PERIODIC:
        return false; // Handled by timer only

      case RotationTiming.WRITE_COUNT:
        return this.writeCount % this.rotationConfig.writeCountThreshold === 0;

      case RotationTiming.HYBRID: {
        // Check if enough time has passed OR enough writes have occurred
        const timeSinceLastCheck = Date.now() - this.lastRotationCheck;
        const timeThreshold = this.rotationConfig.checkInterval / 2; // Check more frequently than timer
        const writeThreshold = this.writeCount % this.rotationConfig.writeCountThreshold === 0;

        return timeSinceLastCheck > timeThreshold || writeThreshold;
      }
      default:
        return false;
    }
  }

  /**
   * Check if rotation is needed for a specific log file
   */
  private needsRotation(logFilePath: string): boolean {
    try {
      if (!fs.existsSync(logFilePath)) {
        return false;
      }
      const stats = fs.statSync(logFilePath);
      return stats.size >= this.rotationConfig.maxFileSize;
    }
    catch {
      return false;
    }
  }

  /**
   * Get the appropriate file extension based on the compression setting
  */
  private getRotatedFileName(baseFilename: string, extension: string, index: number, compressed?: boolean): string {
    const baseName = `${baseFilename}.${index}${extension}`;
    if (compressed ?? this.rotationConfig.compressRotated) {
      return `${baseName}.gz`;
    }
    return baseName;
  }

  /**
   * Compress a file using gzip
   */
  private async compressFile(inputPath: string, outputPath: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const readStream = fs.createReadStream(inputPath);
      const writeStream = fs.createWriteStream(outputPath);
      const gzipStream = zlib.createGzip();

      readStream
        .pipe(gzipStream)
        .pipe(writeStream)
        .on('finish', () => {
          // Remove the original file after a successful compression
          try {
            fs.unlinkSync(inputPath);
            resolve();
          }
          catch (error: any) {
            reject(error instanceof Error ? error : new Error(error));
          }
        })
        .on('error', reject);
    });
  }

  /**
   * Rotate the log file if it exceeds max size
   */
  private rotateLogIfNeeded(logFilePath: string): void {
    if (this.isRotating || !this.needsRotation(logFilePath)) {
      return;
    }

    this.isRotating = true;

    try {
      const baseFilename = path.basename(logFilePath, path.extname(logFilePath));
      const extension = path.extname(logFilePath);
      const directory = path.dirname(logFilePath);

      // Remove the oldest backup if we've reached max files
      const oldestBackup = path.join(directory, this.getRotatedFileName(baseFilename, extension, this.rotationConfig.maxFiles));
      if (fs.existsSync(oldestBackup)) {
        fs.unlinkSync(oldestBackup);
      }

      // Shift all backup files
      for (let i = this.rotationConfig.maxFiles - 1; i >= 1; i--) {
        const currentBackup = path.join(directory, this.getRotatedFileName(baseFilename, extension, i));
        const nextBackup = path.join(directory, this.getRotatedFileName(baseFilename, extension, i + 1));

        if (fs.existsSync(currentBackup)) {
          fs.renameSync(currentBackup, nextBackup);
        }
      }

      // Handle the current log file
      const firstBackup = path.join(directory, this.getRotatedFileName(baseFilename, extension, 1, false));
      fs.renameSync(logFilePath, firstBackup);

      if (this.rotationConfig.compressRotated) {
        const backupCompressed = path.join(directory, this.getRotatedFileName(baseFilename, extension, 1));
        // Compress asynchronously
        this.compressFile(firstBackup, backupCompressed).catch((error) => {
          console.error('Failed to compress rotated log file:', error);
        });
      }
    }
    catch (error) {
      console.error('Failed to rotate log file:', error);
    }
    finally {
      this.isRotating = false;
    }
  }

  /**
   * Check and rotate all log files
   */
  private async checkAndRotateAllLogs(): Promise<void> {
    this.rotateLogIfNeeded(this.logFilePath);
    this.lastRotationCheck = Date.now();
  }

  /**
   * Initialize the rotation timer for periodic checking
   */
  initializeRotationTimer(): void {
    startPromise(this.checkAndRotateAllLogs());
    if (this.rotationConfig.timing === RotationTiming.PERIODIC
      || this.rotationConfig.timing === RotationTiming.HYBRID) {
      this.rotationTimer = setInterval(() => {
        startPromise(this.checkAndRotateAllLogs());
      }, this.rotationConfig.checkInterval);
    }
  }

  /**
   * Stop rotation timer
   */
  stopRotationTimer(): void {
    if (this.rotationTimer) {
      clearInterval(this.rotationTimer);
      this.rotationTimer = null;
    }
  }

  /**
   * Increments the count of writes by one.
   *
   * @return {void} No return value.
   */
  incrementWriteCount(): void {
    this.writeCount++;
  }

  /**
   * Checks if log rotation is necessary and performs the rotation based on the configured timing.
   * If the timing is set to BEFORE_WRITE, the rotation is performed immediately.
   * Otherwise, the rotation is executed on a deferred background task.
   *
   * @return {void} Does not return any value.
   */
  checkRotation(): void {
    if (this.shouldCheckRotation()) {
      if (this.rotationConfig.timing === RotationTiming.BEFORE_WRITE) {
        this.rotateLogIfNeeded(this.logFilePath);
      }
      else {
        setTimeout(() => {
          try {
            this.rotateLogIfNeeded(this.logFilePath);
          }
          catch (error: any) {
            console.error('Background rotation failed:', error);
          }
        }, 0);
      }
    }
  }

  updateLogDirectory(logDirectory: string) {
    this.logDirectory = logDirectory;
  }

  updateRotationConfig(rotationConfig: LogRotationConfig) {
    this.rotationConfig = rotationConfig;
  }
}
