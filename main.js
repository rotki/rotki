const electron = require('electron');
const app = electron.app;
const ipcMain = electron.ipcMain;
const BrowserWindow = electron.BrowserWindow;
const path = require('path');

/*************************************************************
 * window management
 *************************************************************/
let mainWindow = null;

const createWindow = () => {
    mainWindow = new BrowserWindow({width: 800, height: 600});
    mainWindow.loadURL(require('url').format({
        pathname: path.join(__dirname,  'ui', 'index.html'),
        protocol: 'file:',
        slashes: true
    }));
    mainWindow.webContents.openDevTools();

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
};

app.on('ready', createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (mainWindow === null) {
        createWindow();
    }
});

/*************************************************************
 * py process
 *************************************************************/

const PY_DIST_FOLDER = 'NOTAPPPLICABLE';
const PY_FOLDER = 'rotkehlchen';
const PY_MODULE = 'server'; // without .py suffix

let pyProc = null;
let pyPort = null;

const guessPackaged = () => {
    const fullPath = path.join(__dirname, PY_DIST_FOLDER);
    return require('fs').existsSync(fullPath);
};

const getScriptPath = () => {
    if (!guessPackaged()) {
        return path.join(__dirname, PY_FOLDER, PY_MODULE + '.py');
    }
    if (process.platform === 'win32') {
        return path.join(__dirname, PY_DIST_FOLDER, PY_MODULE, PY_MODULE + '.exe');
    }
    return path.join(__dirname, PY_DIST_FOLDER, PY_MODULE, PY_MODULE);
};

const selectPort = () => {
    pyPort = 4242;
    return pyPort;
};

var pyproc_fail_notifier = null;

// Listen for ack messages from renderer process
ipcMain.on('ack', (event, arg) => {
    // when ack is received stop the pyproc fail notifier
    clearInterval(pyproc_fail_notifier);
});

const createPyProc = () => {
    let script = getScriptPath();
    let port = '' + selectPort();

    if (guessPackaged()) {
        console.log("At guess packaged");
        pyProc = require('child_process').execFile(script, [port]);
    } else {
        console.log("At not packaged: script:" + script + " port: " + port);
        pyProc = require('child_process').spawn('python', ["-m", "rotkehlchen", "--zerorpc-port", port, "--ethrpc-port", "8545"]);
    }

    pyProc.on('error', (err) => {
        console.log('Failed to start python subprocess.');
    });
    pyProc.on('exit', function (code, signal) {
        console.log("python subprocess killed with signal " + signal + " and code " +code);
        if (code != 0) {
            // Notify main window every 2 seconds until it acks the notification
            pyproc_fail_notifier = setInterval(function () {
                mainWindow.webContents.send('failed', 'failed');
            }, 2000);
        }
    });

    if (pyProc != null) {
        console.log('child process success on port ' + port);
    }
    console.log("CREATED PYPROCESS");
};

const exitPyProc = () => {
    console.log("KILLING PYPROCESS");
    pyProc.kill();
    pyProc = null;
    pyPort = null;
};

app.on('ready', createPyProc);
app.on('will-quit', exitPyProc);
