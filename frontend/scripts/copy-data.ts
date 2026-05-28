import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { cancel, intro, isCancel, multiselect, outro } from '@clack/prompts';
import { cac } from 'cac';
import consola from 'consola';
import { baseDataDir, copyTree } from './dev-instance';

const APP_NAME = 'rotki';
const DATA_DIR = 'data';
const DEVELOP_DATA_DIR = 'develop_data';
const USER_DIR = 'users';

function copyAndLog(src: string, dst: string): void {
  copyTree(src, dst, {
    preserveMtime: true,
    onFile: ({ src: s, dst: d }) => consola.info(`Copying ${s} to ${d}`),
  });
}

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
    message: 'Select what to copy from data to develop_data (submit empty to skip).',
    options: dataDirs,
    required: false,
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
    copyTree(sourceUserDir, targetUserDir, { preserveMtime: true });
  }

  for (const selectedDir of selectedDataDirs) {
    const sourceDataDir = path.join(dataDir, selectedDir);
    const targetDataDir = path.join(developDataDir, selectedDir);
    if (fs.existsSync(targetDataDir)) {
      consola.info(`Removing ${targetDataDir}`);
      fs.rmSync(targetDataDir, { recursive: true });
    }
    consola.info(`Copying ${sourceDataDir} to ${targetDataDir}`);
    copyTree(sourceDataDir, targetDataDir, { preserveMtime: true });
  }

  outro('Copying is complete.');
}

function copyData(appDataDir: string): void {
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

  copyAndLog(dataDir, developDataDir);

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
