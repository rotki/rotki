import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { cancel, intro, isCancel, multiselect, outro } from '@clack/prompts';
import { cac } from 'cac';
import consola from 'consola';
import { baseDataDir, buildSeedSkip, copyTree, type CopyTreeOptions, type WalkSkip } from './dev-instance';

const APP_NAME = 'rotki';
const DATA_DIR = 'data';
const DEVELOP_DATA_DIR = 'develop_data';
const USER_DIR = 'users';

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
 * the root itself is checked here. Otherwise copying a selected `logs/` would
 * carry over the very tree the skip list exists to exclude.
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

function copyAndLog(src: string, dst: string, includeBackups: boolean): void {
  copyPath(src, dst, {
    ...copyTreeOptions(includeBackups),
    onFile: ({ src: s, dst: d }) => consola.info(`Copying ${s} to ${d}`),
  });
}

async function promptUser(appDataDir: string, includeBackups: boolean): Promise<void> {
  intro('Select which users and data directories to copy from data to develop_data.');
  const dataDir = path.join(appDataDir, DATA_DIR);
  const developDataDir = path.join(appDataDir, DEVELOP_DATA_DIR);

  const userDataDir = path.join(dataDir, USER_DIR);
  const developUserDataDir = path.join(developDataDir, USER_DIR);

  const skip = buildSeedSkip({ includeBackups });

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

  logSkipNotice(includeBackups);

  for (const user of selectedUsers) {
    const sourceUserDir = path.join(userDataDir, user);
    const targetUserDir = path.join(developUserDataDir, user);
    if (fs.existsSync(targetUserDir)) {
      consola.info(`Removing ${targetUserDir}`);
      fs.rmSync(targetUserDir, { recursive: true });
    }
    consola.info(`Copying ${sourceUserDir} to ${targetUserDir}`);
    copyAndLog(sourceUserDir, targetUserDir, includeBackups);
  }

  for (const selectedDir of selectedDataDirs) {
    const sourceDataDir = path.join(dataDir, selectedDir);
    const targetDataDir = path.join(developDataDir, selectedDir);
    if (fs.existsSync(targetDataDir)) {
      consola.info(`Removing ${targetDataDir}`);
      fs.rmSync(targetDataDir, { recursive: true });
    }
    consola.info(`Copying ${sourceDataDir} to ${targetDataDir}`);
    copyAndLog(sourceDataDir, targetDataDir, includeBackups);
  }

  outro('Copying is complete.');
}

function copyData(appDataDir: string, includeBackups: boolean): void {
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

  const dirContents = fs.readdirSync(dataDir);
  consola.info(`Preparing to copy ${dirContents.length} files/directories from ${dataDir} to ${developDataDir}`);
  logSkipNotice(includeBackups);

  copyAndLog(dataDir, developDataDir, includeBackups);

  consola.success(`Copied all content from ${dataDir} to ${developDataDir}`);
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
  .action(async (options) => {
    const dataDir = resolveDataDirectory();
    const includeBackups = options.includeBackups === true;

    if (options.replace) {
      copyData(dataDir, includeBackups);
    }
    else {
      await promptUser(dataDir, includeBackups);
    }
  });

cli.help();
cli.parse();
