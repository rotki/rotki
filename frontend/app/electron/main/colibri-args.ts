import process from 'node:process';
import path from 'node:path';
import { assert } from '@rotki/common';

export class ColibriConfigBuilder {
  private readonly args: string[] = [];
  private cmd: string = '';
  private workDir: string = '../../';

  withPort(port: number): this {
    assert(this.cmd !== '', 'Command must be set first');
    this.args.push(`--port=${port}`);
    return this;
  }

  withLogfilePath(logFilePath: string): this {
    assert(this.cmd !== '', 'Command must be set first');
    this.args.push(`--logfile-path=${logFilePath}`);
    return this;
  }

  withDataDirectory(dataDir?: string): this {
    if (!dataDir) {
      return this;
    }
    assert(this.cmd !== '', 'Command must be set first');
    this.args.push(`--data-directory=${dataDir}`);
    return this;
  }

  withLogLevel(logLevel: string): this {
    assert(this.cmd !== '', 'Command must be set first');
    this.args.push(`--log-level=${logLevel}`);
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
