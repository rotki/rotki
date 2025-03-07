import type { BackendOptions } from '@shared/ipc';
import path from 'node:path';
import process from 'node:process';
import { assert } from '@rotki/common';
import { LogLevel } from '@shared/log-level';

export class ColibriConfigBuilder {
  private readonly args: string[] = [];
  private cmd: string = '';
  private workDir: string = '../../';

  withCors(url: string) {
    assert(this.cmd !== '', 'Command must be set first');
    const corsUrl = url.endsWith('/')
      ? url.slice(0, Math.max(0, url.length - 1))
      : url;
    this.args.push(`--api-cors=${corsUrl}`);
    return this;
  }

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
    if (isDev) {
      const devServerUrl = import.meta.env.VITE_DEV_SERVER_URL as string;
      return baseConfig.setCommand('cargo').setWorkDir('../../colibri').withCors(devServerUrl);
    }
    else {
      return baseConfig.setCommand('colibri').setWorkDir(path.join(resourcesDir, 'colibri')).withCors('app://*');
    }
  },
};
