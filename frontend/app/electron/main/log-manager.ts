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
    private logfiles: string[],
    private rotationConfig: LogRotationConfig,
  ) {

  }

  /**
     * Determine if rotation check should happen based on timing strategy
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
  private getRotatedFileName(baseFilename: string, extension: string, index: number): string {
    if (this.rotationConfig.compressRotated) {
      return `${baseFilename}.${index}${extension}.gz`;
    }
    return `${baseFilename}.${index}${extension}`;
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
          catch (error) {
            reject(error);
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
      const firstBackup = path.join(directory, this.getRotatedFileName(baseFilename, extension, 1));

      if (this.rotationConfig.compressRotated) {
        // Compress asynchronously
        this.compressFile(logFilePath, firstBackup).catch((error) => {
          console.error('Failed to compress rotated log file:', error);
          try {
            const uncompressedBackup = path.join(directory, `${baseFilename}.1${extension}`);
            fs.renameSync(logFilePath, uncompressedBackup);
          }
          catch (renameError) {
            console.error('Failed to rename log file after compression failure:', renameError);
          }
        });
      }
      else {
        fs.renameSync(logFilePath, firstBackup);
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
    for (const logfile of this.logfiles) {
      this.rotateLogIfNeeded(logfile);
    }

    await this.compressExistingRotatedLogs();
    this.cleanupOldLogs();

    this.lastRotationCheck = Date.now();
  }

  /**
     * Manually compress existing rotated log files
     */
  async compressExistingRotatedLogs(): Promise<void> {
    if (!this.rotationConfig.compressRotated) {
      return;
    }

    try {
      for (const logfile of this.logfiles) {
        const baseFilename = path.basename(logfile, path.extname(logfile));
        const extension = path.extname(logfile);

        // Look for uncompressed rotated files and compress them
        for (let i = 1; i <= this.rotationConfig.maxFiles; i++) {
          const uncompressedFile = path.join(this.logDirectory, `${baseFilename}.${i}${extension}`);
          const compressedFile = path.join(this.logDirectory, `${baseFilename}.${i}${extension}.gz`);

          if (fs.existsSync(uncompressedFile) && !fs.existsSync(compressedFile)) {
            await this.compressFile(uncompressedFile, compressedFile);
          }
        }
      }
    }
    catch (error) {
      console.error('Failed to compress existing rotated logs:', error);
    }
  }

  /**
   * Clean up old log files beyond the rotation limit
   */
  cleanupOldLogs(): void {
    try {
      for (const logFile of this.logfiles) {
        const baseFilename = path.basename(logFile, path.extname(logFile));
        const extension = path.extname(logFile);

        // Clean up backup files beyond our rotation limit (both compressed and uncompressed)
        for (let i = this.rotationConfig.maxFiles + 1; i <= this.rotationConfig.maxFiles + 10; i++) {
          const backupFile = path.join(this.logDirectory, `${baseFilename}.${i}${extension}`);
          const compressedBackupFile = path.join(this.logDirectory, `${baseFilename}.${i}${extension}.gz`);

          if (fs.existsSync(backupFile)) {
            fs.unlinkSync(backupFile);
          }
          if (fs.existsSync(compressedBackupFile)) {
            fs.unlinkSync(compressedBackupFile);
          }
        }
      }
    }
    catch (error) {
      console.error('Failed to cleanup old logs:', error);
    }
  }

  /**
     * Initialize the rotation timer for periodic checking
     */
  initializeRotationTimer(): void {
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

  incrementWriteCount(): void {
    this.writeCount++;
  }

  checkRotation() {
    if (this.shouldCheckRotation()) {
      if (this.rotationConfig.timing === RotationTiming.BEFORE_WRITE) {
        this.rotateLogIfNeeded(this.logfiles[0]);
      }
      else {
        setTimeout(() => {
          try {
            this.rotateLogIfNeeded(this.logfiles[0]);
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
