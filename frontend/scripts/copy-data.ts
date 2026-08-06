import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { cancel, intro, isCancel, multiselect, outro, spinner } from '@clack/prompts';
import { cac } from 'cac';
import consola from 'consola';
import { baseDataDir, buildSeedSkip, copyTree, type CopyTreeOptions, humanBytes, type WalkSkip } from './dev-instance';

const APP_NAME = 'rotki';
const DATA_DIR = 'data';
const DEVELOP_DATA_DIR = 'develop_data';
const USER_DIR = 'users';
const PROGRESS_INTERVAL_MS = 150;

interface CopyOptions {
  includeBackups: boolean;
  verbose: boolean;
}

interface CopyStats {
  files: number;
  bytes: number;
}

/**
 * Copying uses the same skip list as seeding: live logs and SQLite WAL/SHM
 * companions are never carried over (copying WAL/SHM would corrupt the copied
 * DB), and `*.backup` files are skipped unless `--include-backups` is passed.
 */
function copyTreeOptions(includeBackups: boolean): CopyTreeOptions {
  return {
    preserveMtime: true,
    skip: buildSeedSkip({ includeBackups }),
  };
}

/** Sorted names of the entries in `dir` that the skip list does not reject. */
function listCopyable(dir: string, skip: WalkSkip): string[] {
  return fs.readdirSync(dir, { withFileTypes: true })
    .filter(entry => !skip(entry.name, entry.isDirectory()))
    .map(entry => entry.name)
    .sort();
}

function logSkipNotice(includeBackups: boolean): void {
  consola.info(includeBackups
    ? 'Skipping logs and SQLite WAL/SHM files'
    : 'Skipping logs, SQLite WAL/SHM and *.backup files (pass --include-backups to copy backups)');
}

/**
 * Copies a single entry, which may be a directory tree or a lone file.
 *
 * `copyTree` only applies `skip` to entries *inside* the root it is given, so
 * the root itself is checked here. Otherwise copying `logs/` as its own unit
 * would carry over the very tree the skip list exists to exclude.
 */
function copyPath(src: string, dst: string, options: CopyTreeOptions): void {
  const isDir = fs.statSync(src).isDirectory();
  if (options.skip?.(path.basename(src), isDir)) {
    return;
  }
  if (isDir) {
    copyTree(src, dst, options);
    return;
  }
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.copyFileSync(src, dst);
  const size = fs.statSync(dst).size;
  if (options.preserveMtime) {
    const stat = fs.statSync(src);
    fs.utimesSync(dst, stat.atime, stat.mtime);
  }
  options.onFile?.({ src, dst, size });
}

/**
 * Copies one labelled entry. Quiet by default: a single progress line per
 * entry that ends with its file count and size. `--verbose` logs every file
 * instead, as this script used to do unconditionally.
 */
function copyEntry(src: string, dst: string, label: string, options: CopyOptions): CopyStats {
  const stats: CopyStats = { files: 0, bytes: 0 };
  const progress = options.verbose ? undefined : spinner();
  let lastEmit = 0;

  progress?.start(`Copying ${label}`);
  try {
    copyPath(src, dst, {
      ...copyTreeOptions(options.includeBackups),
      onFile: ({ src: s, dst: d, size }) => {
        stats.files += 1;
        stats.bytes += size;
        if (options.verbose) {
          consola.info(`Copying ${s} to ${d}`);
          return;
        }
        const now = Date.now();
        if (now - lastEmit >= PROGRESS_INTERVAL_MS) {
          lastEmit = now;
          progress?.message(`Copying ${label} (${stats.files} files, ${humanBytes(stats.bytes)})`);
        }
      },
    });
  }
  catch (error) {
    progress?.stop(`Failed to copy ${label}`);
    throw error;
  }

  const summary = `Copied ${label} (${stats.files} files, ${humanBytes(stats.bytes)})`;
  if (progress) {
    progress.stop(summary);
  }
  else {
    consola.success(summary);
  }
  return stats;
}

function totalOf(stats: CopyStats[]): CopyStats {
  return stats.reduce((acc, s) => ({ files: acc.files + s.files, bytes: acc.bytes + s.bytes }), { files: 0, bytes: 0 });
}

async function promptUser(appDataDir: string, options: CopyOptions): Promise<void> {
  intro('Select which users and data directories to copy from data to develop_data.');
  const dataDir = path.join(appDataDir, DATA_DIR);
  const developDataDir = path.join(appDataDir, DEVELOP_DATA_DIR);

  const userDataDir = path.join(dataDir, USER_DIR);
  const developUserDataDir = path.join(developDataDir, USER_DIR);

  const skip = buildSeedSkip({ includeBackups: options.includeBackups });

  const availableUsers = listCopyable(userDataDir, skip).map(item => ({
    value: item,
    label: item,
  }));

  const selectedUsers = await multiselect({
    message: 'Select which users to copy from data to develop_data.',
    options: availableUsers,
    required: true,
  });

  if (isCancel(selectedUsers)) {
    cancel('Operation cancelled.');
    process.exit(0);
  }

  const dataDirs = listCopyable(dataDir, skip)
    .filter(x => x !== USER_DIR)
    .map(item => ({
      value: item,
      label: item,
    }));

  const selectedDataDirs = await multiselect({
    message: 'Select what to copy from data to develop_data (submit empty to skip).',
    options: dataDirs,
    required: false,
  });

  if (isCancel(selectedDataDirs)) {
    cancel('Operation cancelled.');
    process.exit(0);
  }

  logSkipNotice(options.includeBackups);

  const stats: CopyStats[] = [];

  for (const user of selectedUsers) {
    const sourceUserDir = path.join(userDataDir, user);
    const targetUserDir = path.join(developUserDataDir, user);
    if (fs.existsSync(targetUserDir)) {
      consola.info(`Removing ${targetUserDir}`);
      fs.rmSync(targetUserDir, { recursive: true });
    }
    stats.push(copyEntry(sourceUserDir, targetUserDir, `${USER_DIR}/${user}`, options));
  }

  for (const selectedDir of selectedDataDirs) {
    const sourceDataDir = path.join(dataDir, selectedDir);
    const targetDataDir = path.join(developDataDir, selectedDir);
    if (fs.existsSync(targetDataDir)) {
      consola.info(`Removing ${targetDataDir}`);
      fs.rmSync(targetDataDir, { recursive: true });
    }
    stats.push(copyEntry(sourceDataDir, targetDataDir, selectedDir, options));
  }

  const total = totalOf(stats);
  outro(`Copying is complete (${total.files} files, ${humanBytes(total.bytes)}).`);
}

/**
 * The units the copy reports on: every top-level entry of the data dir, except
 * `users/`, which is expanded so each user directory gets its own line. Entries
 * the skip list rejects outright are dropped so they never get a progress line.
 */
function copyUnits(dataDir: string, includeBackups: boolean): string[] {
  const skip = buildSeedSkip({ includeBackups });
  const units: string[] = [];
  for (const item of listCopyable(dataDir, skip)) {
    const full = path.join(dataDir, item);
    if (item === USER_DIR && fs.statSync(full).isDirectory()) {
      units.push(...listCopyable(full, skip).map(user => path.join(USER_DIR, user)));
      continue;
    }
    units.push(item);
  }
  return units;
}

function copyData(appDataDir: string, options: CopyOptions): void {
  const dataDir = path.join(appDataDir, DATA_DIR);
  const developDataDir = path.join(appDataDir, DEVELOP_DATA_DIR);

  const developDirContent = fs.readdirSync(developDataDir);
  consola.info(`Preparing to remove ${developDirContent.length} files/directories from ${developDataDir}`);
  for (const item of developDirContent) {
    const targetPath = path.join(developDataDir, item);
    consola.info(`Removing ${targetPath}`);
    fs.rmSync(targetPath, { recursive: true });
  }
  consola.success(`Removed content from ${developDataDir}`);

  const units = copyUnits(dataDir, options.includeBackups);
  consola.info(`Preparing to copy ${units.length} entries from ${dataDir} to ${developDataDir}`);
  logSkipNotice(options.includeBackups);

  const stats = units.map(unit => copyEntry(
    path.join(dataDir, unit),
    path.join(developDataDir, unit),
    unit,
    options,
  ));

  const total = totalOf(stats);
  consola.success(`Copied ${total.files} files (${humanBytes(total.bytes)}) from ${dataDir} to ${developDataDir}`);
}

function resolveDataDirectory(): string {
  const appDataDir = path.join(baseDataDir(), APP_NAME);
  if (!fs.existsSync(appDataDir)) {
    throw new Error(`Data directory ${appDataDir} does not exist`);
  }
  return appDataDir;
}

const cli = cac();

cli.command('', 'Copy data from the data folder to the develop_data folder')
  .option('-r, --replace', 'Replaces the existing data in the develop_data folder with data from the data folder', {
    default: false,
  })
  .option('--include-backups', 'Include `*.backup` files in the copy (default: skipped to keep the copy lean)', {
    default: false,
  })
  .option('-v, --verbose', 'Log every copied file instead of one progress line per directory', {
    default: false,
  })
  .action(async (cliOptions) => {
    const dataDir = resolveDataDirectory();
    const options: CopyOptions = {
      includeBackups: cliOptions.includeBackups === true,
      verbose: cliOptions.verbose === true,
    };

    if (cliOptions.replace) {
      copyData(dataDir, options);
    }
    else {
      await promptUser(dataDir, options);
    }
  });

cli.help();
cli.parse();
