import type { BackendOptions } from '@shared/ipc';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { assert } from '@rotki/common';

const BACKEND_DIRECTORY = 'backend';

export class RotkiCoreConfigBuilder {
  private readonly args: string[] = [];
  private cmd: string = '';
  private workDir: string = '../../';

  withCorsUrl(url: string): this {
    assert(this.cmd !== '', 'Command must be set first');
    this.args.push('--api-cors', url.endsWith('/')
      ? url.slice(0, Math.max(0, url.length - 1))
      : url);
    return this;
  }

  withLogFile(path: string): this {
    assert(this.cmd !== '', 'Command must be set first');
    this.args.push('--logfile', path);
    return this;
  }

  withPort(port: number): this {
    assert(this.cmd !== '', 'Command must be set first');
    this.args.push('--rest-api-port', port.toString());
    return this;
  }

  withBackendOptions(options: Partial<BackendOptions>): this {
    if (options.loglevel)
      this.args.push('--loglevel', options.loglevel);

    if (options.logFromOtherModules)
      this.args.push('--logfromothermodules');

    if (options.dataDirectory)
      this.args.push('--data-dir', options.dataDirectory);

    if (options.sleepSeconds)
      this.args.push('--sleep-secs', options.sleepSeconds.toString());

    if (options.maxLogfilesNum)
      this.args.push('--max-logfiles-num', options.maxLogfilesNum.toString());

    if (options.maxSizeInMbAllLogs)
      this.args.push('--max-size-in-mb-all-logs', options.maxSizeInMbAllLogs.toString());

    if (options.sqliteInstructions !== undefined)
      this.args.push('--sqlite-instructions', options.sqliteInstructions.toString());

    return this;
  }

  setWorkDir(workDir: string): this {
    assert(workDir !== '', 'Work dir must be set');
    this.workDir = workDir;
    return this;
  }

  setCommand(cmd: string, args?: string[]): this {
    assert(cmd !== '', 'Command must be set');
    this.cmd = cmd;
    this.args.push(...args ?? []);
    return this;
  }

  build(): { command: string; args: string[]; workDir: string } {
    return { command: this.cmd, args: this.args, workDir: this.workDir };
  }
}

export class RotkiConfigError extends Error {
  constructor(message?: string, readonly terminate = false) {
    super(message);
    this.name = 'RotkiConfigError';
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export const RotkiCoreConfig = {
  create(isDev: boolean, options: Partial<BackendOptions>): RotkiCoreConfigBuilder {
    const profilingCmd = process.env.ROTKI_BACKEND_PROFILING_CMD;
    const profilingArgs = process.env.ROTKI_BACKEND_PROFILING_ARGS;

    const builder = new RotkiCoreConfigBuilder();
    let command: RotkiCoreConfigBuilder;

    if (isDev) {
      const devServerUrl = import.meta.env.VITE_DEV_SERVER_URL as string;
      const pythonArgs = ['-m', 'rotkehlchen'];
      if (profilingCmd) {
        command = builder.setCommand(
          profilingCmd,
          profilingArgs?.split(' '),
        ).withCorsUrl(devServerUrl);
      }
      else {
        command = builder.setCommand('python', pythonArgs)
          .withCorsUrl(devServerUrl);
      }
    }
    else {
      const resources = process.resourcesPath ? process.resourcesPath : import.meta.dirname;
      const binaryDirectory = os.platform() === 'darwin'
        ? path.join(resources, BACKEND_DIRECTORY, 'rotki-core')
        : path.join(resources, BACKEND_DIRECTORY);

      const files = fs.readdirSync(binaryDirectory);

      if (files.length === 0) {
        throw new RotkiConfigError('No backend binaries found', false);
      }

      const binaries = files.filter(file => file.startsWith('rotki-core-'));

      if (binaries.length > 1) {
        const names = files.join(', ');
        const error = `Expected only one backend binary but found multiple ones
       in directory: ${names}.\nThis might indicate a problematic upgrade.\n\n
       Please make sure only one binary file exists that matches the app version`;
        throw new RotkiConfigError(error, true);
      }

      command = builder.setCommand(binaries[0])
        .setWorkDir(binaryDirectory)
        .withCorsUrl('app://*');
    }

    return command.withBackendOptions(options);
  },
};
