import process from 'node:process';
import path from 'node:path';
import { assert } from '@rotki/common';
import { LogLevel } from '@shared/log-level';
import type { BackendOptions } from '@shared/ipc';

export class ColibriConfigBuilder {
  private readonly args: string[] = [];
  private cmd: string = '';
  private workDir: string = '../../';

  withPort(port: number): this {
    assert(this.cmd !== '', 'Command must be set first');
    this.args.push(`--port=${port}`);
    return this;
  }

  withBackendOptions(options: Partial<BackendOptions>): this {
    assert(this.cmd !== '', 'Command must be set first');
    const { dataDirectory, loglevel = LogLevel.INFO, maxLogfilesNum, maxSizeInMbAllLogs } = options;

    if (dataDirectory) {
      this.args.push(`--data-directory=${dataDirectory}`);
    }

    this.args.push(`--log-level=${loglevel}`);

    if (maxLogfilesNum) {
      this.args.push(`--max-logfiles-num=${maxLogfilesNum}`);
    }

    if (maxSizeInMbAllLogs) {
      const maxLogs = maxLogfilesNum ?? 5;
      const maxSize = Math.round(maxSizeInMbAllLogs / maxLogs);
      this.args.push(`--max-size-in-mb=${maxSize}`);
    }
    return this;
  }

  withLogfilePath(logFilePath: string): this {
    assert(this.cmd !== '', 'Command must be set first');
    this.args.push(`--logfile-path=${logFilePath}`);
    return this;
  }

  setWorkDir(workDir: string): this {
    assert(workDir !== '', 'Work dir must be set');
    this.workDir = workDir;
    return this;
  }

  setCommand(cmd: string): this {
    assert(cmd !== '', 'Command must be set');
    this.cmd = cmd;
    if (cmd === 'cargo') {
      this.args.push('run', '--');
    }
    return this;
  }

  build(): { command: string; args: string[]; workDir: string } {
    assert(this.cmd !== '', 'Command must be set');
    return { command: this.cmd, args: this.args, workDir: this.workDir };
  }
}

export const ColibriConfig = {
  create(isDev: boolean): ColibriConfigBuilder {
    const baseConfig = new ColibriConfigBuilder();
    const resourcesDir = process.resourcesPath ? process.resourcesPath : import.meta.dirname;
    return isDev
      ? baseConfig.setCommand('cargo').setWorkDir('../../colibri')
      : baseConfig.setCommand('colibri').setWorkDir(path.join(resourcesDir, 'colibri'));
  },
};
