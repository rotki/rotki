import * as Electron from 'electron';
import { app } from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import { ChildProcess, spawn, execFile } from 'child_process';
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
    this.ELECTRON_LOG_PATH = `${this.logsPath}rotki_electron.log`;
    fs.writeFileSync(
      this.ELECTRON_LOG_PATH,
      'Rotki Electron Log initialization\n'
    );
  }

  private logToFile(msg: string | Error) {
    console.log(msg);
    fs.appendFileSync(this.ELECTRON_LOG_PATH, `${msg}\n`);
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

    if (this.guessPackaged()) {
      this.startProcessPackaged(port, args);
    } else {
      this.startProcess(port, args);
    }

    let childProcess = this.childProcess;
    if (!childProcess) {
      return;
    }
    childProcess.on('error', (err: Error) => {
      this.logToFile(err);
      this.logToFile('Failed to start python subprocess.');
    });

    const handler = this;
    childProcess.on('exit', (code: number, signal: any) => {
      this.logToFile(
        `python subprocess killed with signal ${signal} and code ${code}`
      );
      if (code !== 0) {
        // Notify main window every 2 seconds until it acks the notification
        handler.setNotification(window);
      }
    });

    if (childProcess) {
      this.logToFile(
        `Child process started on port: ${port} with pid: ${childProcess.pid}`
      );
    }
    this.logToFile('CREATED PYPROCESS');
  }

  exitPyProc() {
    this.logToFile('KILLING PYPROCESS');
    let client = this.childProcess;
    if (client) {
      client.kill();
      this.childProcess = undefined;
      this.port = undefined;
    }

    if (process.platform === 'win32') {
      this.terminateWindowsProcesses();
    }
  }

  private guessPackaged() {
    const fullPath = path.join(__dirname, PyHandler.PY_DIST_FOLDER);
    return fs.existsSync(fullPath);
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
    let dist_dir = path.join(__dirname, PyHandler.PY_DIST_FOLDER);
    let files = fs.readdirSync(dist_dir);
    if (files.length === 0) {
      this.logAndQuit('No files found in the dist directory');
    } else if (files.length !== 1) {
      this.logAndQuit('Found more than one file in the dist directory');
    }
    let executable = files[0];
    if (!executable.startsWith('rotkehlchen-')) {
      this.logAndQuit(
        'Unexpected executable name "' + executable + '" in the dist directory'
      );
    }
    executable = path.join(dist_dir, executable);
    this.executable = executable;
    this.childProcess = execFile(
      executable,
      ['--zerorpc-port', port.toString()].concat(args)
    );
  }

  private terminateWindowsProcesses() {
    // For win32 we got two problems:
    // 1. pyProc.kill() does not work due to SIGTERM not really being a signal
    //    in Windows
    // 2. the onefile pyinstaller packaging creates two executables.
    // https://github.com/pyinstaller/pyinstaller/issues/2483
    //
    // So the solution is to not let the application close, get all
    // pids and kill them before we close the app

    this.logToFile('Detecting Windows pids');
    const executable = this.executable;

    tasklist().then((tasks: tasklist.Task[]) => {
      this.logToFile(`In task list result for executable: ${executable}`);

      let pidsToKill: number[] = [];

      for (let i = 0; i < tasks.length; i++) {
        if (tasks[i]['imageName'] !== executable) {
          continue;
        }

        pidsToKill.push(tasks[i]['pid']);
        this.logToFile(`Adding PID ${tasks[i].pid}`);
      }

      // now that we have all the pids gathered, call taskkill on them
      this.logToFile('Calling task kill for Windows PIDs');

      let args = ['/f', '/t'];

      for (let i = 0; i < pidsToKill.length; i++) {
        args.push('/PID');
        args.push(pidsToKill[i].toString());
      }
      this.logToFile(
        'Calling Task kill and args: ' + JSON.stringify(args, null, 4)
      );

      const taskKill = spawn('taskkill', args);

      taskKill.on('exit', () => {
        this.logToFile('Task kill exited');
        app.exit();
      });

      taskKill.on('error', err => {
        this.logToFile('Task kill failed:' + err);
        app.exit();
      });
    });
  }

  private loadArgumentsFromFile(args: string[]) {
    // try to see if there is a configfile
    if (fs.existsSync('rotki_config.json')) {
      let raw_data: Buffer = fs.readFileSync('rotki_config.json');

      try {
        let jsondata = JSON.parse(raw_data.toString());
        if (jsondata.hasOwnProperty('loglevel')) {
          args.push('--loglevel', jsondata['loglevel']);
        }
        if (jsondata.hasOwnProperty('logfromothermodules')) {
          if (jsondata['logfromothermodules'] === true) {
            args.push('--logfromothermodules');
          }
        }
        if (jsondata.hasOwnProperty('logfile')) {
          args.push('--logfile', jsondata['logfile']);
        }
        if (jsondata.hasOwnProperty('data-dir')) {
          args.push('--data-dir', jsondata['data-dir']);
        }
        if (jsondata.hasOwnProperty('sleep-secs')) {
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
