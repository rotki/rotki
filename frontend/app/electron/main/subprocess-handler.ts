/* eslint-disable max-lines */

import { type ChildProcess, spawn, spawnSync } from 'node:child_process';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import process from 'node:process';
import { Buffer } from 'node:buffer';
import { type App, type BrowserWindow, app, ipcMain } from 'electron';
import psList from 'ps-list';
import { assert } from '@rotki/common';
import { type Task, tasklist } from 'tasklist';
import { DEFAULT_PORT, selectPort } from '@electron/main/port-utils';
import { checkIfDevelopment, wait } from '@shared/utils';
import { BackendCode, type BackendOptions } from '@shared/ipc';
import type stream from 'node:stream';

const isDevelopment = checkIfDevelopment();
const currentDir = import.meta.dirname;

function streamToString(ioStream: stream.Readable, log: (msg: string) => void, label = 'rotki-core'): () => void {
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

    log(`[${label}] ${stringChunks.join('\n')}`);
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

function getBackendArguments(options: Partial<BackendOptions>): string[] {
  const args: string[] = [];
  if (options.loglevel)
    args.push('--loglevel', options.loglevel);

  if (options.logFromOtherModules)
    args.push('--logfromothermodules');

  if (options.dataDirectory)
    args.push('--data-dir', options.dataDirectory);

  if (options.sleepSeconds)
    args.push('--sleep-secs', options.sleepSeconds.toString());

  if (options.maxLogfilesNum)
    args.push('--max-logfiles-num', options.maxLogfilesNum.toString());

  if (options.maxSizeInMbAllLogs)
    args.push('--max-size-in-mb-all-logs', options.maxSizeInMbAllLogs.toString());

  if (options.sqliteInstructions !== undefined)
    args.push('--sqlite-instructions', options.sqliteInstructions.toString());

  return args;
}

const BACKEND_DIRECTORY = 'backend';
const COLIBRI_DIRECTORY = 'colibri';

export class SubprocessHandler {
  readonly defaultLogDirectory: string;
  private rpcFailureNotifier?: any;
  private childProcess?: ChildProcess;
  private colibriProcess?: ChildProcess;
  private executable?: string;
  private _corsURL?: string;
  private backendOutput = '';
  private onChildError?: (err: Error) => void;
  private onChildExit?: (code: number, signal: any) => void;
  private logDirectory?: string;
  private exiting: boolean;
  private stdioListeners = {
    outOff: (): void => {},
    errOff: (): void => {},
  };

  constructor(private app: App) {
    this.exiting = false;
    app.setAppLogsPath(path.join(app.getPath('appData'), 'rotki', 'logs'));
    this.defaultLogDirectory = app.getPath('logs');
    this._serverUrl = '';
    const startupMessage = `
    ------------------
    | Starting rotki |
    ------------------`;
    this.logToFile(startupMessage);
    this.listenForMessages();
  }

  private _port?: number;

  get port(): number {
    assert(this._port);
    return this._port;
  }

  private _serverUrl: string;

  get serverUrl(): string {
    return this._serverUrl;
  }

  get logDir(): string {
    if (import.meta.env.VITE_DEV_LOGS)
      return path.join('frontend', 'logs');

    return this.logDirectory ?? this.defaultLogDirectory;
  }

  get electronLogFile(): string {
    return path.join(this.logDir, 'rotki_electron.log');
  }

  get backendLogFile(): string {
    return path.join(this.logDir, 'rotkehlchen.log');
  }

  private static packagedBackendPath() {
    const resources = process.resourcesPath ? process.resourcesPath : currentDir;
    if (os.platform() === 'darwin')
      return path.join(resources, BACKEND_DIRECTORY, 'rotki-core');

    return path.join(resources, BACKEND_DIRECTORY);
  }

  private static packagedColibriPath() {
    const resources = process.resourcesPath ? process.resourcesPath : currentDir;
    return path.join(resources, COLIBRI_DIRECTORY);
  }

  /**
   * Removes the error/out listeners from the backend when the app is quiting.
   * It should be called `before-quit` to avoid having weird unhandled exceptions on SIGINT.
   */
  quitting(): void {
    this.stdioListeners.errOff();
    this.stdioListeners.outOff();
  }

  logToFile(msg: string | Error) {
    try {
      if (!msg)
        return;

      const message = `${new Date(Date.now()).toISOString()}: ${msg.toString()}`;

      // eslint-disable-next-line no-console
      console.log(message);
      if (!fs.existsSync(this.logDir))
        fs.mkdirSync(this.logDir);

      fs.appendFileSync(this.electronLogFile, `${message}\n`);
    }
    catch {
      // Not much we can do if an error happens here.
    }
  }

  setCorsURL(url: string) {
    if (url.endsWith('/'))
      this._corsURL = url.slice(0, Math.max(0, url.length - 1));
    else this._corsURL = url;
  }

  listenForMessages() {
    // Listen for ack messages from renderer process
    ipcMain.on('ack', (event, ...args) => {
      if (args[0] === 1)
        clearInterval(this.rpcFailureNotifier);
      else this.logToFile(`Warning: unknown ack code ${args[0]}`);
    });
  }

  logAndQuit(msg: string) {
    // eslint-disable-next-line no-console
    console.log(msg);
    this.app.quit();
  }

  async checkForBackendProcess(): Promise<number[]> {
    const runningProcesses = await psList({ all: true });
    const matches = runningProcesses.filter(
      process => process.cmd?.includes('-m rotkehlchen.start') || process.cmd?.includes('rotki-core'),
    );
    return matches.map(p => p.pid);
  }

  async createPyProc(window: BrowserWindow, options: Partial<BackendOptions>) {
    if (options.logDirectory && !fs.existsSync(options.logDirectory))
      fs.mkdirSync(options.logDirectory);

    this.logDirectory = options.logDirectory;
    if (process.env.SKIP_PYTHON_BACKEND) {
      this.logToFile('Skipped starting rotki-core');
      return;
    }

    if (os.platform() === 'darwin') {
      const release = os.release().split('.');
      if (release.length > 0 && Number.parseInt(release[0]) < 17) {
        this.setFailureNotification(window, 'rotki requires at least macOS High Sierra', BackendCode.MACOS_VERSION);
        return;
      }
    }
    else if (os.platform() === 'win32') {
      const release = os.release().split('.');
      if (release.length > 1) {
        const major = Number.parseInt(release[0]);
        const minor = Number.parseInt(release[1]);

        // Win 7 (v6.1) or earlier
        const v = major + minor * 0.1;
        if (v < 6.1) {
          this.setFailureNotification(
            window,
            'rotki cannot run on Windows 7 or earlier, since Python3.11 is no longer supported there',
            BackendCode.WIN_VERSION,
          );
          return;
        }
      }
    }

    const port = await selectPort();
    const backendUrl = import.meta.env.VITE_BACKEND_URL as string | undefined;

    assert(backendUrl);
    const regExp = /(.*):\/\/(.*):(.*)/;
    const match = backendUrl.match(regExp);
    assert(match && match.length === 4);
    const [, scheme, host, oldPort] = match;
    assert(host);

    if (port !== DEFAULT_PORT && Number.parseInt(oldPort) !== port) {
      this._serverUrl = `${scheme}://${host}:${port}`;
      this.logToFile(`Default port ${oldPort} was in use. Starting rotki-core at ${port}`);
    }

    this._port = port;
    const args: string[] = getBackendArguments(options);

    if (this.guessPackaged())
      this.startProcessPackaged(port, args, window);
    else this.startProcess(port, args);

    const childProcess = this.childProcess;
    if (!childProcess)
      return;

    if (childProcess.stdout)
      this.stdioListeners.outOff = streamToString(childProcess.stdout, msg => this.logBackendOutput(msg));

    if (childProcess.stderr)
      this.stdioListeners.errOff = streamToString(childProcess.stderr, msg => this.logBackendOutput(msg));

    // eslint-disable-next-line @typescript-eslint/no-this-alias
    const handler = this;
    this.onChildError = (err: Error) => {
      this.logToFile(`Encountered an error while trying to start rotki-core\n\n${err.toString()}`);
      // Notify the main window every 2 seconds until it acks the notification
      handler.setFailureNotification(window, err, BackendCode.TERMINATED);
      this.childProcess = undefined;
      this._port = undefined;
    };

    this.onChildExit = (code: number, signal: any) => {
      this.logToFile(`rotki-core exited with signal: ${signal} (Code: ${code})`);
      /**
         * On win32 we can also get a null code on SIGTERM
         */
      if (!(code === 0 || code === null)) {
        // Notify the main window every 2 seconds until it acks the notification
        handler.setFailureNotification(window, this.backendOutput, BackendCode.TERMINATED);
      }
      this.childProcess = undefined;
      this._port = undefined;
    };

    childProcess.once('error', this.onChildError);
    childProcess.once('exit', this.onChildExit);

    if (childProcess) {
      this.logToFile(`rotki-core started on port: ${port} (PID: ${childProcess.pid})`);
      return;
    }
    this.logToFile('rotki-core was not successfully started');
  }

  async exitPyProc(restart = false) {
    const client = this.childProcess;
    if (!client)
      return;

    if (this.exiting)
      return;

    this.exiting = true;
    this.logToFile(restart ? 'Restarting rotki-core' : `Terminating rotki-core: (PID ${client.pid})`);
    if (this.rpcFailureNotifier)
      clearInterval(this.rpcFailureNotifier);

    if (restart && client) {
      if (this.onChildExit)
        client.off('exit', this.onChildExit);

      if (this.onChildError)
        client.off('error', this.onChildError);

      this.stdioListeners.outOff();
      this.stdioListeners.errOff();
    }
    if (process.platform === 'win32')
      await this.terminateWindowsProcesses(restart);

    if (client)
      this.terminateBackend(client);

    this.exiting = false;
  }

  private logBackendOutput(msg: string | Error) {
    this.logToFile(msg);
    this.backendOutput = `${this.backendOutput} ${msg.toString()}`;
  }

  private terminateBackend = (client: ChildProcess): void => {
    if (!client.pid) {
      this.logToFile('subprocess was already terminated (no process id pid found)');
    }
    else {
      if (!client.exitCode) {
        this.logToFile(`attempting to kill process: ${client.pid}`);
        const success = client.kill();
        this.logToFile(`The Python sub-process was terminated successfully (${client.killed}) (${success})`);
      }
    }

    this.childProcess = undefined;
    this._port = undefined;
  };

  private guessPackaged() {
    const path = SubprocessHandler.packagedBackendPath();
    this.logToFile(`Determining if we are packaged by seeing if ${path} exists`);
    return fs.existsSync(path);
  }

  private setFailureNotification(
    window: Electron.BrowserWindow | null,
    backendOutput: string | Error,
    code: BackendCode,
  ): void {
    if (this.rpcFailureNotifier)
      clearInterval(this.rpcFailureNotifier);

    this.rpcFailureNotifier = setInterval(() => {
      /**
       * There is a possibility that the window has been already disposed and this
       * will result in an exception. In that case, we just catch and clear the notifier
       */
      try {
        window?.webContents.send('failed', backendOutput, code);
      }
      catch {
        clearInterval(this.rpcFailureNotifier);
      }
    }, 2000);
  }

  private startProcess(port: number, args: string[]) {
    const profilingCmd = process.env.ROTKI_BACKEND_PROFILING_CMD;
    const profilingArgs = process.env.ROTKI_BACKEND_PROFILING_ARGS;

    const defaultArgs: string[] = [
      ...(profilingArgs ? profilingArgs.split(' ') : []),
      ...(profilingCmd ? ['python'] : []),
      '-m',
      'rotkehlchen.start',
      '--rest-api-port',
      port.toString(),
    ];

    if (this._corsURL)
      defaultArgs.push('--api-cors', this._corsURL);

    defaultArgs.push('--logfile', this.backendLogFile);

    if (!process.env.VIRTUAL_ENV) {
      this.logAndQuit('ERROR: Running in development mode and not inside a python virtual environment');
      return;
    }

    const allArgs = defaultArgs.concat(args);
    const cmd = profilingCmd || 'python';
    this.logToFile(`Starting non-packaged rotki-core: ${cmd} ${allArgs.join(' ')}`);

    this.childProcess = spawn(cmd, allArgs, { cwd: '../../' });

    if (!isDevelopment) {
      this.colibriProcess = spawn('colibri');
      if (this.colibriProcess.stdout)
        streamToString(this.colibriProcess.stdout, msg => this.logToFile(`Colibri says: ${msg}`));
    }
  }

  private startProcessPackaged(port: number, args: string[], window: Electron.CrossProcessExports.BrowserWindow): void {
    const distDir = SubprocessHandler.packagedBackendPath();
    const files = fs.readdirSync(distDir);
    if (files.length === 0) {
      this.logAndQuit('ERROR: No files found in the dist directory');
      return;
    }

    const binaries = files.filter(file => file.startsWith('rotki-core-'));

    if (binaries.length > 1) {
      const names = files.join(', ');
      const error = `Expected only one backend binary but found multiple ones
       in directory: ${names}.\nThis might indicate a problematic upgrade.\n\n
       Please make sure only one binary file exists that matches the app version`;
      this.logToFile(`ERROR: ${error}`);
      this.setFailureNotification(window, error, BackendCode.TERMINATED);
      return;
    }

    const exe = files.find(file => file.startsWith('rotki-core-'));
    if (!exe) {
      this.logAndQuit(`ERROR: Executable was not found`);
      return;
    }

    this.executable = exe;
    const executable = path.join(distDir, exe);
    if (this._corsURL)
      args.push('--api-cors', this._corsURL);

    args.push('--logfile', this.backendLogFile);
    args = ['--rest-api-port', port.toString()].concat(args);
    this.logToFile(`Starting packaged rotki-core: ${executable} ${args.join(' ')}`);
    this.childProcess = spawn(executable, args);

    if (!isDevelopment) {
      const colibriDir = SubprocessHandler.packagedColibriPath();
      const colibriExe = fs.readdirSync(colibriDir).find(file => file.startsWith('colibri'));

      if (!colibriExe) {
        this.logAndQuit(`ERROR: colibri executable was not found`);
        return;
      }
      this.colibriProcess = spawn(path.join(colibriDir, colibriExe));
      if (this.colibriProcess.stdout)
        streamToString(this.colibriProcess.stdout, msg => this.logToFile(`output: ${msg}`), 'colibri');
    }
  }

  private async terminateWindowsProcesses(restart: boolean) {
    // For win32 we got two problems:
    // 1. pyProc.kill() does not work due to SIGTERM not really being a signal
    //    in Windows
    // 2. the onefile pyinstaller packaging creates two executables.
    // https://github.com/pyinstaller/pyinstaller/issues/2483
    //
    // So the solution is to not let the application close, get all
    // pids and kill them before we close the app

    this.logToFile('Starting windows process termination');
    const executable = this.executable;
    if (!executable) {
      this.logToFile('No rotki-core executable detected');
      return;
    }

    const tasks: Task[] = await tasklist();
    this.logToFile(`Currently running: ${tasks.length} tasks`);

    const pids = tasks.filter(task => task.imageName === executable).map(task => task.pid);
    this.logToFile(`Detected the following running rotki-core processes: ${pids.join(', ')}`);

    const args = ['/f', '/t'];

    for (const pid of pids) args.push('/PID', pid.toString());

    this.logToFile(`Preparing to call "taskill ${args.join(' ')}" on the rotki-core processes`);

    try {
      spawnSync('taskkill', args);
      await this.waitForTermination(tasks, pids);
    }
    catch (error: any) {
      this.logToFile(`Call to taskkill failed:\n\n ${error.toString()}`);
    }
    finally {
      this.logToFile('Call to taskkill complete');
      if (!restart)
        app.exit();
    }
  }

  private async waitForTermination(tasks: Task[], processes: number[]) {
    function stillRunning(tasks: Task[]): number {
      return tasks.filter(({ pid }) => processes.includes(pid)).length;
    }

    const running = stillRunning(tasks);
    if (running === 0) {
      this.logToFile('The task killed successfully');
      return;
    }

    for (let i = 0; i < 10; i++) {
      this.logToFile(`The ${running} processes are still running. Waiting for 2 seconds`);
      await wait(2000);
      tasks = await tasklist();
      if (stillRunning(tasks) === 0) {
        this.logToFile('The task killed successfully');
        break;
      }
    }
  }
}
