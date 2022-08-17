import { ChildProcess, spawn } from 'child_process';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import stream from 'stream';
import { app, App, BrowserWindow, ipcMain } from 'electron';
import psList from 'ps-list';
import { Task, tasklist } from 'tasklist';
import { BackendCode } from '@/electron-main/backend-code';
import { BackendOptions } from '@/electron-main/ipc';
import { DEFAULT_PORT, selectPort } from '@/electron-main/port-utils';
import { assert } from '@/utils/assertions';
import { wait } from '@/utils/backoff';

const streamToString = (
  ioStream: stream.Readable,
  log: (msg: string) => void
): (() => void) => {
  const bufferChunks: Buffer[] = [];
  const stringChunks: string[] = [];

  const onData = (chunk: any) => {
    if (typeof chunk === 'string') {
      stringChunks.push(chunk);
    } else {
      bufferChunks.push(chunk);
    }
  };

  const onEnd = () => {
    if (bufferChunks.length > 0) {
      try {
        stringChunks.push(Buffer.concat(bufferChunks).toString('utf8'));
      } catch (e: any) {
        stringChunks.push(e.message);
      }
    }

    log(`[rotki-core] ${stringChunks.join('\n')}`);
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
};

function getBackendArguments(options: Partial<BackendOptions>): string[] {
  const args: string[] = [];
  if (options.loglevel) {
    args.push('--loglevel', options.loglevel);
  }
  if (options.logFromOtherModules) {
    args.push('--logfromothermodules');
  }
  if (options.dataDirectory) {
    args.push('--data-dir', options.dataDirectory);
  }
  if (options.sleepSeconds) {
    args.push('--sleep-secs', options.sleepSeconds.toString());
  }
  if (options.maxLogfilesNum) {
    args.push('--max-logfiles-num', options.maxLogfilesNum.toString());
  }
  if (options.maxSizeInMbAllLogs) {
    args.push(
      '--max-size-in-mb-all-logs',
      options.maxSizeInMbAllLogs.toString()
    );
  }
  if (options.sqliteInstructions !== undefined) {
    args.push('--sqlite-instructions', options.sqliteInstructions.toString());
  }
  return args;
}

const BACKEND_DIRECTORY = 'backend';

export default class PyHandler {
  readonly defaultLogDirectory: string;
  private rpcFailureNotifier?: any;
  private childProcess?: ChildProcess;
  private executable?: string;
  private _corsURL?: string;
  private backendOutput: string = '';
  private onChildError?: (err: Error) => void;
  private onChildExit?: (code: number, signal: any) => void;
  private logDirectory?: string;
  private stdioListeners = {
    outOff: () => {},
    errOff: () => {}
  };

  constructor(private app: App) {
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
    if (import.meta.env.VITE_DEV_LOGS) {
      return path.join('..', 'logs');
    }
    return this.logDirectory ?? this.defaultLogDirectory;
  }

  get electronLogFile(): string {
    return path.join(this.logDir, 'rotki_electron.log');
  }

  get backendLogFile(): string {
    return path.join(this.logDir, 'rotkehlchen.log');
  }

  private static packagedBackendPath() {
    const resources = process.resourcesPath ? process.resourcesPath : __dirname;
    if (os.platform() === 'darwin') {
      return path.join(resources, BACKEND_DIRECTORY, 'rotki-core');
    }
    return path.join(resources, BACKEND_DIRECTORY);
  }

  logToFile(msg: string | Error) {
    try {
      if (!msg) {
        return;
      }
      const message = `${new Date(Date.now()).toISOString()}: ${msg}`;

      console.log(message);
      if (!fs.existsSync(this.logDir)) {
        fs.mkdirSync(this.logDir);
      }
      fs.appendFileSync(this.electronLogFile, `${message}\n`);
    } catch (e) {
      // Not much we can do if an error happens here.
    }
  }

  setCorsURL(url: string) {
    if (url.endsWith('/')) {
      this._corsURL = url.substring(0, url.length - 1);
    } else {
      this._corsURL = url;
    }
  }

  listenForMessages() {
    // Listen for ack messages from renderer process
    ipcMain.on('ack', (event, ...args) => {
      if (args[0] === 1) {
        clearInterval(this.rpcFailureNotifier);
      } else {
        this.logToFile(`Warning: unknown ack code ${args[0]}`);
      }
    });
  }

  logAndQuit(msg: string) {
    console.log(msg);
    this.app.quit();
  }

  async checkForBackendProcess(): Promise<number[]> {
    const runningProcesses = await psList({ all: true });
    const matches = runningProcesses.filter(
      process =>
        process.cmd?.includes('-m rotkehlchen') ||
        process.cmd?.includes('rotki-core')
    );
    return matches.map(p => p.pid);
  }

  async createPyProc(window: BrowserWindow, options: Partial<BackendOptions>) {
    if (options.logDirectory && !fs.existsSync(options.logDirectory)) {
      fs.mkdirSync(options.logDirectory);
    }
    this.logDirectory = options.logDirectory;
    if (process.env.SKIP_PYTHON_BACKEND) {
      this.logToFile('Skipped starting python sub-process');
      return;
    }

    if (os.platform() === 'darwin') {
      const release = os.release().split('.');
      if (release.length > 0 && parseInt(release[0]) < 17) {
        this.setFailureNotification(
          window,
          'rotki requires at least macOS High Sierra',
          BackendCode.MACOS_VERSION
        );
        return;
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

    if (port !== DEFAULT_PORT) {
      if (parseInt(oldPort) !== port) {
        this._serverUrl = `${scheme}://${host}:${port}`;
        this.logToFile(
          `Default port ${oldPort} was in use. Starting backend at ${port}`
        );
      }
    }

    this._port = port;
    const args: string[] = getBackendArguments(options);

    if (this.guessPackaged()) {
      this.startProcessPackaged(port, args, window);
    } else {
      this.startProcess(port, args);
    }

    const childProcess = this.childProcess;
    if (!childProcess) {
      return;
    }
    if (childProcess.stdout) {
      this.stdioListeners.outOff = streamToString(childProcess.stdout, msg =>
        this.logBackendOutput(msg)
      );
    }
    if (childProcess.stderr) {
      this.stdioListeners.errOff = streamToString(childProcess.stderr, msg =>
        this.logBackendOutput(msg)
      );
    }

    const handler = this;
    this.onChildError = (err: Error) => {
      this.logToFile(
        `Encountered an error while trying to start the python sub-process\n\n${err}`
      );
      // Notify the main window every 2 seconds until it acks the notification
      handler.setFailureNotification(window, err, BackendCode.TERMINATED);
    };

    this.onChildExit = (code: number, signal: any) => {
      this.logToFile(
        `The Python sub-process exited with signal: ${signal} (Code: ${code})`
      );
      if (code !== 0) {
        // Notify the main window every 2 seconds until it acks the notification
        handler.setFailureNotification(
          window,
          this.backendOutput,
          BackendCode.TERMINATED
        );
      }
    };

    childProcess.on('error', this.onChildError);
    childProcess.on('exit', this.onChildExit);

    if (childProcess) {
      this.logToFile(
        `The Python sub-process started on port: ${port} (PID: ${childProcess.pid})`
      );
      return;
    }
    this.logToFile('The Python sub-process was not successfully started');
  }

  async exitPyProc(restart: boolean = false) {
    const client = this.childProcess;
    this.logToFile(
      restart ? 'Restarting the backend' : 'Terminating the backend'
    );
    if (this.rpcFailureNotifier) {
      clearInterval(this.rpcFailureNotifier);
    }
    if (restart && client) {
      if (this.onChildExit) {
        client.off('exit', this.onChildExit);
      }
      if (this.onChildError) {
        client.off('error', this.onChildError);
      }
      this.stdioListeners.outOff();
      this.stdioListeners.errOff();
    }
    if (process.platform === 'win32') {
      return this.terminateWindowsProcesses(restart);
    }
    if (client) {
      return this.terminateBackend(client);
    }
  }

  private logBackendOutput(msg: string | Error) {
    this.logToFile(msg);
    this.backendOutput += msg;
  }

  private terminateBackend = (client: ChildProcess) =>
    new Promise<void>((resolve, reject) => {
      if (!client.pid) {
        this.logToFile(
          'subprocess was already terminated (no process id pid found)'
        );
        this.childProcess = undefined;
        this._port = undefined;
        resolve();
        return;
      }

      client.on('exit', () => {
        this.logToFile(
          `The Python sub-process was terminated successfully (${client.killed})`
        );
        resolve();
        this.childProcess = undefined;
        this._port = undefined;
      });
      client.on('error', e => {
        reject(e);
      });
      client.kill();
    });

  private guessPackaged() {
    const path = PyHandler.packagedBackendPath();
    this.logToFile(
      `Determining if we are packaged by seeing if ${path} exists`
    );
    return fs.existsSync(path);
  }

  private setFailureNotification(
    window: Electron.BrowserWindow | null,
    backendOutput: string | Error,
    code: BackendCode
  ) {
    if (this.rpcFailureNotifier) {
      clearInterval(this.rpcFailureNotifier);
    }
    this.rpcFailureNotifier = setInterval(function () {
      window?.webContents.send('failed', backendOutput, code);
    }, 2000);
  }

  private startProcess(port: number, args: string[]) {
    const defaultArgs: string[] = [
      '-m',
      'rotkehlchen',
      '--rest-api-port',
      port.toString()
    ];

    if (this._corsURL) {
      defaultArgs.push('--api-cors', this._corsURL);
    }

    defaultArgs.push('--logfile', this.backendLogFile);

    if (!process.env.VIRTUAL_ENV) {
      this.logAndQuit(
        'ERROR: Running in development mode and not inside a python virtual environment'
      );
      return;
    }

    const allArgs = defaultArgs.concat(args);
    this.logToFile(
      `Starting non-packaged python subprocess: python ${allArgs.join(' ')}`
    );

    this.childProcess = spawn('python', allArgs);
  }

  private startProcessPackaged(
    port: number,
    args: string[],
    window: Electron.CrossProcessExports.BrowserWindow
  ) {
    const distDir = PyHandler.packagedBackendPath();
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
    if (this._corsURL) {
      args.push('--api-cors', this._corsURL);
    }
    args.push('--logfile', this.backendLogFile);
    args = ['--rest-api-port', port.toString()].concat(args);
    this.logToFile(
      `Starting packaged python subprocess: ${executable} ${args.join(' ')}`
    );
    this.childProcess = spawn(executable, args);
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
      this.logToFile('No python sub-process executable detected');
      return;
    }

    const tasks: Task[] = await tasklist();
    this.logToFile(`Currently running: ${tasks.length} tasks`);

    const pids = tasks
      .filter(task => task.imageName === executable)
      .map(task => task.pid);
    this.logToFile(
      `Detected the following running python sub-processes: ${pids.join(', ')}`
    );

    const args = ['/f', '/t'];

    for (let i = 0; i < pids.length; i++) {
      args.push('/PID');
      args.push(pids[i].toString());
    }

    this.logToFile(
      `Preparing to call "taskill ${args.join(
        ' '
      )}" on the python sub-processes`
    );

    const taskKill = spawn('taskkill', args);

    return new Promise<void>(resolve => {
      taskKill.on('exit', () => {
        this.logToFile('Call to taskkill exited');
        if (!restart) {
          app.exit();
        }

        this.waitForTermination(tasks, pids).then(resolve);
      });

      taskKill.on('error', err => {
        this.logToFile(`Call to taskkill failed:\n\n ${err}`);
        if (!restart) {
          app.exit();
        }
        resolve();
      });

      setTimeout(() => resolve, 15000);
    });
  }

  private async waitForTermination(tasks: Task[], processes: number[]) {
    function stillRunning() {
      return tasks.filter(({ pid }) => processes.includes(pid)).length;
    }

    let running = stillRunning();
    if (running === 0) {
      return;
    }

    for (let i = 0; i < 10; i++) {
      this.logToFile(
        `The ${running} processes are still running. Waiting for 2 seconds`
      );
      await wait(2000);
      running = stillRunning();
      if (stillRunning.length === 0) {
        break;
      }
    }
  }
}
