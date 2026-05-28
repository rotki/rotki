import fs from 'node:fs';
import path from 'node:path';
import consola from 'consola';

import { errorMessage } from './format';

const logger = consola.withTag('dev-instance:fs-walk');

/**
 * Files we never carry over from a live rotki data dir: SQLite WAL/SHM
 * companion files (carrying them would corrupt the seeded DB) and live logs.
 */
const SEED_HARD_SKIP_PATTERNS = [/\.log$/i, /\.sqlite-wal$/i, /\.sqlite-shm$/i, /\.db-wal$/i, /\.db-shm$/i];
const SEED_HARD_SKIP_DIRS = new Set(['logs']);

/** Soft-skipped: not copied by default; pass `includeBackups: true` to opt in. */
const SEED_BACKUP_PATTERNS = [/\.backup$/i];

export interface SeedSkipOptions {
  /** When true, includes `*.backup` files in the seed. Default: false. */
  includeBackups?: boolean;
}

export function buildSeedSkip(opts: SeedSkipOptions = {}): WalkSkip {
  return (name: string, isDir: boolean): boolean => {
    if (isDir)
      return SEED_HARD_SKIP_DIRS.has(name.toLowerCase());
    if (SEED_HARD_SKIP_PATTERNS.some(p => p.test(name)))
      return true;
    if (!opts.includeBackups && SEED_BACKUP_PATTERNS.some(p => p.test(name)))
      return true;
    return false;
  };
}

/** Convenience: default skip predicate (no backups). */
export const shouldSkipSeedEntry = buildSeedSkip();

export type WalkSkip = (name: string, isDir: boolean) => boolean;

export function walkFiles(root: string, onFile: (full: string, size: number) => void, skip?: WalkSkip): void {
  const visit = (current: string): void => {
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    }
    catch {
      return;
    }
    for (const entry of entries) {
      if (skip?.(entry.name, entry.isDirectory())) {
        continue;
      }
      const full = path.join(current, entry.name);
      try {
        if (entry.isDirectory()) {
          visit(full);
        }
        else if (entry.isFile()) {
          onFile(full, fs.statSync(full).size);
        }
      }
      catch {
        // unreadable entries are skipped
      }
    }
  };
  visit(root);
}

export function dirSizeBytes(dir: string, skip?: WalkSkip): number {
  let total = 0;
  walkFiles(dir, (_, size) => {
    total += size;
  }, skip);
  return total;
}

export function estimateSeedSize(source: string, opts: SeedSkipOptions = {}): number {
  return dirSizeBytes(source, buildSeedSkip(opts));
}

export function freeDiskBytes(targetDir: string): number | undefined {
  try {
    const probeDir = fs.existsSync(targetDir) ? targetDir : path.dirname(targetDir);
    const stat = fs.statfsSync(probeDir);
    return stat.bavail * stat.bsize;
  }
  catch (error) {
    logger.warn(`Failed to read free disk space at ${targetDir}: ${errorMessage(error)}`);
    return undefined;
  }
}

export interface CopyTreeOptions {
  /** Predicate to skip an entry by name. Default: copy everything. */
  skip?: WalkSkip;
  /** Preserve source file mtime/atime on the destination. Default: false. */
  preserveMtime?: boolean;
  /**
   * Called per file copied, with byte size. Useful for progress reporting.
   * Aggregation/throttling is the caller's responsibility.
   */
  onFile?: (info: { src: string; dst: string; size: number }) => void;
}

/**
 * Recursively copies `sourceDir` → `targetDir` preserving directory layout.
 * Symlinks are recreated as symlinks (never followed). Errors propagate; the
 * caller decides whether to clean up the partial copy.
 */
export function copyTree(sourceDir: string, targetDir: string, opts: CopyTreeOptions = {}): void {
  const walk = (src: string, dst: string): void => {
    fs.mkdirSync(dst, { recursive: true });
    const entries = fs.readdirSync(src, { withFileTypes: true });
    for (const entry of entries) {
      if (opts.skip?.(entry.name, entry.isDirectory())) {
        continue;
      }
      const srcPath = path.join(src, entry.name);
      const dstPath = path.join(dst, entry.name);
      if (entry.isSymbolicLink()) {
        const link = fs.readlinkSync(srcPath);
        fs.symlinkSync(link, dstPath);
      }
      else if (entry.isDirectory()) {
        walk(srcPath, dstPath);
      }
      else if (entry.isFile()) {
        fs.copyFileSync(srcPath, dstPath);
        const size = fs.statSync(dstPath).size;
        if (opts.preserveMtime) {
          const stat = fs.statSync(srcPath);
          fs.utimesSync(dstPath, stat.atime, stat.mtime);
        }
        opts.onFile?.({ src: srcPath, dst: dstPath, size });
      }
    }
  };
  walk(sourceDir, targetDir);
}

export interface SeedProgress {
  files: number;
  bytes: number;
}

export interface SeedInstanceOptions extends SeedSkipOptions {
  onProgress?: (p: SeedProgress) => void;
}

export function seedInstance(
  targetDir: string,
  sourceDir: string,
  opts: SeedInstanceOptions = {},
): void {
  fs.mkdirSync(targetDir, { recursive: true });
  const progress: SeedProgress = { files: 0, bytes: 0 };
  const lastEmit = { time: Date.now(), bytes: 0 };

  const emit = (): void => {
    const now = Date.now();
    if (now - lastEmit.time >= 250 || progress.bytes - lastEmit.bytes >= 500 * 1024 * 1024) {
      opts.onProgress?.(progress);
      lastEmit.time = now;
      lastEmit.bytes = progress.bytes;
    }
  };

  try {
    copyTree(sourceDir, targetDir, {
      skip: buildSeedSkip({ includeBackups: opts.includeBackups }),
      onFile: ({ size }) => {
        progress.files += 1;
        progress.bytes += size;
        emit();
      },
    });
    opts.onProgress?.(progress);
  }
  catch (error) {
    logger.error(`Seed copy failed: ${errorMessage(error)}`);
    fs.rmSync(targetDir, { recursive: true, force: true });
    throw error;
  }
}
