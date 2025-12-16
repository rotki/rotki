import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { cancel, intro, isCancel, multiselect, outro } from '@clack/prompts';
import { cac } from 'cac';
import consola from 'consola';

const APP_NAME = 'rotki';
const DATA_DIR = 'data';
const DEVELOP_DATA_DIR = 'develop_data';
const USER_DIR = 'users';

async function promptUser(appDataDir: string): Promise<void> {
  intro('Select which users and data directories to copy from data to develop_data.');
  const dataDir = path.join(appDataDir, DATA_DIR);
  const developDataDir = path.join(appDataDir, DEVELOP_DATA_DIR);

  const userDataDir = path.join(dataDir, USER_DIR);
  const developUserDataDir = path.join(developDataDir, USER_DIR);

  const availableUsers = fs.readdirSync(userDataDir).map(item => ({
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

  const dataDirs = fs.readdirSync(dataDir)
    .filter(x => x !== USER_DIR)
    .map(item => ({
      value: item,
      label: item,
    }));

  const selectedDataDirs = await multiselect({
    message: 'Select what to copy from data to develop_data.',
    options: dataDirs,
    required: true,
  });

  if (isCancel(selectedDataDirs)) {
    cancel('Operation cancelled.');
    process.exit(0);
  }

  for (const user of selectedUsers) {
    const sourceUserDir = path.join(userDataDir, user);
    const targetUserDir = path.join(developUserDataDir, user);
    if (fs.existsSync(targetUserDir)) {
      consola.info(`Removing ${targetUserDir}`);
      fs.rmSync(targetUserDir, { recursive: true });
    }
    consola.info(`Copying ${sourceUserDir} to ${targetUserDir}`);
    copyDir(sourceUserDir, targetUserDir);
  }

  for (const selectedDir of selectedDataDirs) {
    const sourceDataDir = path.join(dataDir, selectedDir);
    const targetDataDir = path.join(developDataDir, selectedDir);
    if (fs.existsSync(targetDataDir)) {
      consola.info(`Removing ${targetDataDir}`);
      fs.rmSync(targetDataDir, { recursive: true });
    }
    consola.info(`Copying ${sourceDataDir} to ${targetDataDir}`);
    copyDir(sourceDataDir, targetDataDir);
  }

  outro('Copying is complete.');
}

function copyFile(src: string, dest: string): void {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
  const stats = fs.statSync(src);
  fs.utimesSync(dest, stats.atime, stats.mtime);
}

function copyDir(src: string, dest: string, log = false): void {
  fs.mkdirSync(dest, { recursive: true });
  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (log) {
      consola.info(`Copying ${srcPath} to ${destPath}`);
    }

    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    }
    else {
      copyFile(srcPath, destPath);
    }
  }
}

function copyData(appDataDir: string) {
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
  consola.info(`Preparing to Copy ${dirContents.length} files/directories from ${dataDir} to ${developDataDir}`);

  copyDir(dataDir, developDataDir, true);

  consola.success(`Copied all content from ${dataDir} to ${developDataDir}`);
}

function resolveDataDirectory(): string {
  const platform = os.platform();
  const homedir = os.homedir();

  let baseDir: string;

  switch (platform) {
    case 'win32':
      baseDir = process.env.LOCALAPPDATA ?? path.join(homedir, 'AppData', 'Local');
      break;

    case 'darwin':
      baseDir = path.join(homedir, 'Library', 'Application Support');
      break;

    case 'linux':
      baseDir = process.env.XDG_DATA_HOME ?? path.join(homedir, '.local', 'share');
      break;

    default:
      baseDir = path.join(homedir, '.local', 'share');
  }

  const appDataDir = path.join(baseDir, APP_NAME);

  if (!fs.existsSync(appDataDir)) {
    throw new Error(`Data directory ${appDataDir} does not exist`);
  }

  return appDataDir;
}

const cli = cac();

cli.command('', 'Copy data from the data folder to the develop_data folder')
  .option('--replace', 'Replaces the existing data in the develop_data folder with data from the data folder', {
    default: false,
  })
  .action(async (options) => {
    const dataDir = resolveDataDirectory();

    if (options.replace) {
      copyData(dataDir);
    }
    else {
      await promptUser(dataDir);
    }
  });

cli.help();
cli.parse();
