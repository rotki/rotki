import { ChildProcess, execFile, spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { app, App, BrowserWindow, ipcMain } from 'electron';
import tasklist from 'tasklist';
import { assert } from '@/utils/assertions';

export default class PyHandler {
  private static PY_DIST_FOLDER = 'rotkehlchen_py_dist';
  private rpcFailureNotifier?: any;
  private childProcess?: ChildProcess;
  private _port?: number;
  private executable?: string;
  private readonly logsPath: string;
  private readonly ELECTRON_LOG_PATH: string;
  private _corsURL?: string;

  get port(): number {
    assert(this._port != null);
    return this._port;
  }

  constructor(private app: App) {
    app.setAppLogsPath(path.join(app.getPath('appData'), 'rotki', 'logs'));
    this.logsPath = app.getPath('logs');
    this.ELECTRON_LOG_PATH = path.join(this.logsPath, 'rotki_electron.log');
    fs.writeFileSync(
      this.ELECTRON_LOG_PATH,
      'Rotki Electron Log initialization\n'
    );
  }

  private logToFile(msg: string | Error) {
    const message = `${new Date(Date.now()).toISOString()}: ${msg}`;
    console.log(message);
    fs.appendFileSync(this.ELECTRON_LOG_PATH, `${message}\n`);
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
      if (args[0] == 1) {
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

  createPyProc(window: BrowserWindow) {
    if (process.env.SKIP_PYTHON_BACKEND) {
      this.logToFile('Skipped starting python sub-process');
      return;
    }

    const port = this.selectPort();
    const args: string[] = [];
    this.loadArgumentsFromFile(args);

    if (this.guessPackaged()) {
      this.startProcessPackaged(port, args);
    } else {
      this.startProcess(port, args);
    }

    const childProcess = this.childProcess;
    if (!childProcess) {
      return;
    }
    childProcess.on('error', (err: Error) => {
      this.logToFile(
        `Encountered an error while trying to start the python sub-process\n\n${err}`
      );
    });

    const handler = this;
    childProcess.on('exit', (code: number, signal: any) => {
      this.logToFile(
        `The Python sub-process exited with signal: ${signal} (Code: ${code})`
      );
      if (code !== 0) {
        // Notify the main window every 2 seconds until it acks the notification
        handler.setFailureNotification(window);
      }
    });

    if (childProcess) {
      this.logToFile(
        `The Python sub-process started on port: ${port} (PID: ${childProcess.pid})`
      );
      return;
    }
    this.logToFile('The Python sub-process was not successfully started');
  }

  async exitPyProc() {
    this.logToFile('Exiting the application');
    if (this.rpcFailureNotifier) {
      clearInterval(this.rpcFailureNotifier);
    }
    if (process.platform === 'win32') {
      await this.terminateWindowsProcesses();
    } else {
      const client = this.childProcess;
      if (client) {
        client.kill();
        this.logToFile(
          `The Python sub-process was terminated successfully (${client.killed})`
        );
        this.childProcess = undefined;
        this._port = undefined;
      }
    }
  }

  private guessPackaged() {
    const path = PyHandler.packagedBackendPath();
    this.logToFile(
      `Determining if we are packaged by seeing if ${path} exists`
    );
    return fs.existsSync(path);
  }

  private static packagedBackendPath() {
    const resources = process.resourcesPath ? process.resourcesPath : __dirname;
    return path.join(resources, PyHandler.PY_DIST_FOLDER);
  }

  private selectPort() {
    // TODO: Perhaps find free port and return it here?
    this._port = 4242;
    return this._port;
  }

  private setFailureNotification(window: Electron.BrowserWindow | null) {
    this.rpcFailureNotifier = setInterval(function () {
      window?.webContents.send('failed', 'failed');
    }, 2000);
  }

  private startProcess(port: number, args: string[]) {
    const defaultArgs: string[] = [
      '-m',
      'rotkehlchen',
      '--api-port',
      port.toString()
    ];

    if (this._corsURL) {
      defaultArgs.push('--api-cors', this._corsURL);
    }

    defaultArgs.push('--logfile', path.join(this.logsPath, 'rotkehlchen.log'));

    if (process.env.ROTKEHLCHEN_ENVIRONMENT === 'test') {
      const tempPath = path.join(this.app.getPath('temp'), 'rotkehlchen');
      if (!fs.existsSync(tempPath)) {
        fs.mkdirSync(tempPath);
      }
      defaultArgs.push('--data-dir', tempPath);
    }
    // in some systems the virtualenv's python is not detected from inside electron and the
    // system python is used. Electron/node seemed to add /usr/bin to the path before the
    // virtualenv directory and as such system's python is used. Not sure why this happens only
    // in some systems. Check again in the future if this happens in Lefteris laptop Archlinux.
    // To mitigate this if a virtualenv is detected we add its bin directory to the start
    // start of the path
    if (process.env.VIRTUAL_ENV) {
      process.env.PATH =
        process.env.VIRTUAL_ENV +
        path.sep +
        (process.platform === 'win32' ? 'Scripts;' : 'bin:') +
        process.env.PATH;
    } else {
      this.logAndQuit(
        'ERROR: Running in development mode and not inside a python virtual environment'
      );
    }

    this.logToFile(
      `Starting non-packaged python subprocess: python ${defaultArgs.join(' ')}`
    );
    this.childProcess = spawn('python', defaultArgs.concat(args));
  }

  private startProcessPackaged(port: number, args: string[]) {
    const dist_dir = PyHandler.packagedBackendPath();
    const files = fs.readdirSync(dist_dir);
    if (files.length === 0) {
      this.logAndQuit('ERROR: No files found in the dist directory');
    } else if (files.length !== 1) {
      this.logAndQuit('ERROR: Found more than one file in the dist directory');
    }
    let executable = files[0];
    if (!executable.startsWith('rotkehlchen-')) {
      this.logAndQuit(
        `ERROR: Unexpected executable name "${executable}" in the dist directory`
      );
    }
    this.executable = executable;
    executable = path.join(dist_dir, executable);
    if (this._corsURL) {
      args.push('--api-cors', this._corsURL);
    }
    args.push('--logfile', path.join(this.logsPath, 'rotkehlchen.log'));
    args = ['--api-port', port.toString()].concat(args);
    this.logToFile(
      `Starting packaged python subprocess: ${executable} ${args.join(' ')}`
    );
    this.childProcess = execFile(executable, args);
  }

  private async terminateWindowsProcesses() {
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

    const tasks: tasklist.Task[] = await tasklist();
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

    taskKill.on('exit', () => {
      this.logToFile('Call to taskkill exited');
      app.exit();
    });

    taskKill.on('error', err => {
      this.logToFile(`Call to taskkill failed:\n\n ${err}`);
      app.exit();
    });
  }

  private loadArgumentsFromFile(args: string[]) {
    // try to see if there is a configfile
    if (fs.existsSync('rotki_config.json')) {
      const raw_data: Buffer = fs.readFileSync('rotki_config.json');

      try {
        const jsondata = JSON.parse(raw_data.toString());
        if (Object.prototype.hasOwnProperty.call(jsondata, 'loglevel')) {
          args.push('--loglevel', jsondata['loglevel']);
        }
        if (
          Object.prototype.hasOwnProperty.call(jsondata, 'logfromothermodules')
        ) {
          if (jsondata['logfromothermodules'] === true) {
            args.push('--logfromothermodules');
          }
        }
        if (Object.prototype.hasOwnProperty.call(jsondata, 'logfile')) {
          args.push('--logfile', jsondata['logfile']);
        }
        if (Object.prototype.hasOwnProperty.call(jsondata, 'data-dir')) {
          args.push('--data-dir', jsondata['data-dir']);
        }
        if (Object.prototype.hasOwnProperty.call(jsondata, 'sleep-secs')) {
          args.push('--sleep-secs', jsondata['sleep-secs']);
        }
      } catch (e) {
        // do nothing, act as if there is no config given
        // TODO: Perhaps in the future warn the user inside
        // the app that there is a config file with invalid json
        this.logToFile(
          `Could not read the rotki_config.json file due to: "${e}". Proceeding normally without a config file ...`
        );
      }
    }
  }
}
