import * as Electron from 'electron';
import { app } from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import { ChildProcess, execFile, spawn } from 'child_process';
import tasklist from 'tasklist';
import ipcMain = Electron.ipcMain;
import App = Electron.App;
import BrowserWindow = Electron.BrowserWindow;

export default class PyHandler {
  private static PY_DIST_FOLDER = 'rotkehlchen_py_dist';
  private rpcFailureNotifier?: any;
  private childProcess?: ChildProcess;
  private port?: number;
  private executable?: string;
  private readonly logsPath: string;
  private readonly ELECTRON_LOG_PATH: string;

  constructor(private app: App) {
    if (process.platform === 'linux') {
      this.logsPath = app.getPath('appData');
    } else {
      this.logsPath = app.getPath('logs');
    }
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

  listenForMessages() {
    // Listen for ack messages from renderer process
    ipcMain.on('ack', () => {
      // when ack is received stop the pyproc fail notifier
      clearInterval(this.rpcFailureNotifier);
    });
  }

  logAndQuit(msg: string) {
    console.log(msg);
    this.app.quit();
  }

  createPyProc(window: BrowserWindow) {
    let port = this.selectPort();
    let args: string[] = [];
    this.loadArgumentsFromFile(args);

    if (PyHandler.guessPackaged()) {
      this.startProcessPackaged(port, args);
    } else {
      this.startProcess(port, args);
    }

    let childProcess = this.childProcess;
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
        handler.setNotification(window);
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

    if (process.platform === 'win32') {
      await this.terminateWindowsProcesses();
    } else {
      let client = this.childProcess;
      if (client) {
        client.kill();
        this.logToFile(
          `The Python sub-process was terminated successfully (${client.killed})`
        );
        this.childProcess = undefined;
        this.port = undefined;
      }
    }
  }

  private static guessPackaged() {
    return fs.existsSync(PyHandler.packagedBackendPath());
  }

  private static packagedBackendPath() {
    const resources = process.resourcesPath ? process.resourcesPath : __dirname;
    return path.join(resources, PyHandler.PY_DIST_FOLDER);
  }

  private selectPort() {
    // TODO: Perhaps find free port and return it here?
    this.port = 4242;
    return this.port;
  }

  private setNotification(window: Electron.BrowserWindow) {
    this.rpcFailureNotifier = setInterval(function() {
      window.webContents.send('failed', 'failed');
    }, 2000);
  }

  private startProcess(port: number, args: string[]) {
    let defaultArgs: string[] = [
      '-m',
      'rotkehlchen',
      '--zerorpc-port',
      port.toString()
    ];

    if (process.env.ROTKEHLCHEN_ENVIRONMENT === 'test') {
      let tempPath = path.join(this.app.getPath('temp'), 'rotkehlchen');
      if (!fs.existsSync(tempPath)) {
        fs.mkdirSync(tempPath);
      }
      defaultArgs.push('--data-dir', tempPath);
    }

    this.childProcess = spawn('python', defaultArgs.concat(args));
  }

  private startProcessPackaged(port: number, args: string[]) {
    let dist_dir = PyHandler.packagedBackendPath();
    let files = fs.readdirSync(dist_dir);
    if (files.length === 0) {
      this.logAndQuit('No files found in the dist directory');
    } else if (files.length !== 1) {
      this.logAndQuit('Found more than one file in the dist directory');
    }
    let executable = files[0];
    if (!executable.startsWith('rotkehlchen-')) {
      this.logAndQuit(
        `Unexpected executable name "${executable}" in the dist directory`
      );
    }
    this.executable = executable;
    executable = path.join(dist_dir, executable);
    this.childProcess = execFile(
      executable,
      ['--zerorpc-port', port.toString()].concat(args)
    );
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
      let raw_data: Buffer = fs.readFileSync('rotki_config.json');

      try {
        let jsondata = JSON.parse(raw_data.toString());
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
          `Could not read the rotki_config.json file due to: "${e}". Proceeding normally without a config file ....`
        );
      }
    }
  }
}
