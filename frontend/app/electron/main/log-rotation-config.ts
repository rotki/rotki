export enum RotationTiming {
  BEFORE_WRITE = 'before_write',
  PERIODIC = 'periodic',
  WRITE_COUNT = 'write_count',
  HYBRID = 'hybrid',
}

export interface LogRotationConfig {
  maxFileSize: number; // in bytes
  maxFiles: number;
  compressRotated: boolean; // whether to gzip rotated files
  timing: RotationTiming;
  checkInterval: number; // For periodic timing (ms)
  writeCountThreshold: number; // For write count timing
}
