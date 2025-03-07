import type stream from 'node:stream';
import { Buffer } from 'node:buffer';
import { type ChildProcess, spawn, spawnSync } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';
import { wait } from '@shared/utils';
import { type Task, tasklist } from 'tasklist';

type OnErrorHandler = (error: Error) => void;

type OnExitHandler = (code: number, signal: any) => void;

type OnExitHandlerWithLastError = (code: number, signal: any, lastError: string) => void;

export class ProcessManager {
  private process?: ChildProcess;
  private isExiting: boolean = false;
  private cleanupHandlers: Array<() => void> = [];
  private command: string = '';
  private lastError: string = '';
  private onErrorHandler?: OnErrorHandler;
  private onExitHandler?: OnExitHandler;

  constructor(
    private readonly processName: string,
    private readonly log: (msg: string) => void,
    private readonly options: {
      useWindowsTermination?: boolean;
      maxTerminationAttempts?: number;
    } = {},
  ) {}

  private setupStreamReader(ioStream: stream.Readable, label: 'error' | 'log'): () => void {
    const bufferChunks: Buffer[] = [];
    const stringChunks: string[] = [];

    const onData = (chunk: any): void => {
      if (typeof chunk === 'string')
        stringChunks.push(chunk);
      else
        bufferChunks.push(chunk);
    };

    const onEnd = (): void => {
      if (bufferChunks.length > 0) {
        try {
          stringChunks.push(Buffer.concat(bufferChunks).toString('utf8'));
        }
        catch (error: any) {
          stringChunks.push(error.message);
        }
      }

      const logMessage = stringChunks.join('\n');
      this.log(`[${this.processName}:${label}] ${logMessage}`);
      if (label === 'error') {
        this.lastError = logMessage;
      }
    };

    const onError = (err: Error) => {
      console.error(err);
    };

    ioStream.on('data', onData);
    ioStream.on('error', onError);
    ioStream.on('end', onEnd);

    return () => {
      ioStream.off('data', onData);
      ioStream.off('end', onEnd);
      ioStream.off('error', onError);
    };
  }

  start(command: string, args: string[], cwd?: string) {
    this.log(`Starting ${this.processName} in ${cwd} with command: ${command} ${args.join(' ')}`);
    this.command = command;
    const commandPath = cwd && path.isAbsolute(cwd) ? path.join(cwd, command) : command;
    this.process = spawn(commandPath, args, { cwd });

    if (this.onErrorHandler) {
      this.process.on('error', this.onErrorHandler);
    }

    if (this.onExitHandler) {
      this.process.on('exit', this.onExitHandler);
    }

    if (this.process.stdout) {
      const redirectOut = this.setupStreamReader(this.process.stdout, 'log');
      this.cleanupHandlers.push(redirectOut);
    }

    if (this.process.stderr) {
      const redirectError = this.setupStreamReader(this.process.stderr, 'error');
      this.cleanupHandlers.push(redirectError);
    }

    this.log(`Started ${this.processName} with PID: ${this.process.pid}`);
    return this.process;
  }

  onExit(handler: OnExitHandlerWithLastError): void {
    const handlerWithLastError = (code: number, signal: any) => {
      handler(code, signal, this.lastError);
    };
    this.onExitHandler = handlerWithLastError;
    this.process?.once('exit', handlerWithLastError);
    this.cleanupHandlers.push(() => {
      this.onExitHandler = undefined;
      this.process?.off('exit', handlerWithLastError);
    });
  }

  onError(handler: OnErrorHandler) {
    this.onErrorHandler = handler;
    this.process?.once('error', handler);
    this.cleanupHandlers.push(() => {
      this.onErrorHandler = undefined;
      this.process?.off('error', handler);
    });
  }

  async terminate() {
    if (!this.process || this.isExiting) {
      return;
    }

    this.isExiting = true;
    this.log(`Terminating ${this.processName} (PID: ${this.process.pid})`);

    try {
      if (process.platform === 'win32' && this.options.useWindowsTermination) {
        await this.terminateWindowsProcesses();
      }
      else {
        this.process.kill();
      }
    }
    catch (error: any) {
      this.log(`Failed to terminate ${this.processName}: ${error.toString()}`);
    }
    finally {
      this.cleanup();
      this.isExiting = false;
    }
  }

  private async terminateWindowsProcesses(): Promise<void> {
    // For win32 we got two problems:
    // 1. pyProc.kill() does not work due to SIGTERM not really being a signal
    //    in Windows
    // 2. the onefile pyinstaller packaging creates two executables.
    // https://github.com/pyinstaller/pyinstaller/issues/2483
    //
    // So the solution is to not let the application close, get all
    // pids and kill them before we close the app

    this.log('Starting windows process termination');
    const tasks: Task[] = await tasklist();
    this.log(`Currently running: ${tasks.length} tasks`);

    const pids = tasks.filter(task => task.imageName === this.command).map(task => task.pid);
    this.log(`Detected the following running rotki-core processes: ${pids.join(', ')}`);

    const args = ['/f', '/t'];

    for (const pid of pids) args.push('/PID', pid.toString());

    this.log(`Preparing to call "taskill ${args.join(' ')}" on the rotki-core processes`);

    try {
      spawnSync('taskkill', args);
      await this.waitForTermination(tasks, pids);
    }
    catch (error: any) {
      this.log(`Call to taskkill failed:\n\n ${error.toString()}`);
    }
    finally {
      this.log('Call to taskkill complete');
    }
  }

  private async waitForTermination(tasks: Task[], processes: number[]) {
    function stillRunning(tasks: Task[]): number {
      return tasks.filter(({ pid }) => processes.includes(pid)).length;
    }

    const running = stillRunning(tasks);
    if (running === 0) {
      this.log('The task killed successfully');
      return;
    }

    for (let i = 0; i < 10; i++) {
      this.log(`The ${running} processes are still running. Waiting for 2 seconds`);
      await wait(2000);
      tasks = await tasklist();
      if (stillRunning(tasks) === 0) {
        this.log('The task killed successfully');
        break;
      }
    }
  }

  private cleanup() {
    this.cleanupHandlers.forEach(handler => handler());
    this.cleanupHandlers = [];
    this.process = undefined;
  }

  get isRunning(): boolean {
    return this.process?.pid !== undefined;
  }

  get pid(): number | undefined {
    return this.process?.pid;
  }
}
