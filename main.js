const electron = require('electron');
const app = electron.app;
const ipcMain = electron.ipcMain;
const BrowserWindow = electron.BrowserWindow;
const path = require('path');
const fs = require('fs');

if (process.env.NODE_ENV !== 'production') {
    require('electron-context-menu')({
        prepend: (params, browserWindow) => [{
            label: 'Rainbow',
            // Only show it when right-clicking images
            visible: params.mediaType === 'image'
        }]
    });
}

/*************************************************************
 * window management
 *************************************************************/
let mainWindow = null;

function disableAnimationsForTest() {
    if (process.env.ROTKEHLCHEN_ENVIRONMENT === 'test') {
        let webContents = mainWindow.webContents;
        webContents.once('dom-ready', () => {
            let code = `
                $(document.body).addClass('no-animations');
                window.jQuery.fx.off = true;
                let pluginDefaults = window.jconfirm.pluginDefaults;
                pluginDefaults.animation = 'none';
                pluginDefaults.closeAnimation = 'none';
                pluginDefaults.backgroundDismissAnimation = 'none';
                pluginDefaults.animationSpeed = 0;
                pluginDefaults.animationBounce = 0;
`;
            mainWindow.webContents.executeJavaScript(code, true)
                .then(value => console.log(value));
        });
    }
}

const createWindow = () => {
    mainWindow = new BrowserWindow({width: 800, height: 600});
    disableAnimationsForTest();

    mainWindow.loadURL(require('url').format({
        pathname: path.join(__dirname, 'ui', 'index.html'),
        protocol: 'file:',
        slashes: true
    }));

    // uncomment for the final app to have dev tools opened
    // mainWindow.webContents.openDevTools();

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

const PY_DIST_FOLDER = 'rotkehlchen_py_dist';

let pyProc = null;
let pyPort = null;

const guessPackaged = () => {
    const fullPath = path.join(__dirname, PY_DIST_FOLDER);
    return fs.existsSync(fullPath);
};

const selectPort = () => {
    // TODO: Perhaps find free port and return it here?
    pyPort = 4242;
    return pyPort;
};

var pyproc_fail_notifier = null;

// Listen for ack messages from renderer process
ipcMain.on('ack', (event, arg) => {
    // when ack is received stop the pyproc fail notifier
    clearInterval(pyproc_fail_notifier);
});

function log_and_quit(msg) {
    console.log(msg);
    app.quit();
}

const createPyProc = () => {
    let port = '' + selectPort();

    if (guessPackaged()) {
        let dist_dir = path.join(__dirname, PY_DIST_FOLDER);
        let files = fs.readdirSync(dist_dir);
        if (files.length === 0) {
            log_and_quit('No files found in the dist directory');
        } else if (files.length !== 1) {
            log_and_quit('Found more than one file in the dist directory');
        }
        let executable = files[0];
        if (!executable.startsWith('rotkehlchen-')) {
            log_and_quit('Unexpected executable name "' + executable + '" in the dist directory');
        }
        executable = path.join(dist_dir, executable);
        pyProc = require('child_process').execFile(executable, ["--zerorpc-port", port]);
    } else {
        let args = ["-m", "rotkehlchen", "--zerorpc-port", port];

        if (process.env.ROTKEHLCHEN_ENVIRONMENT === 'test') {
            let tempPath = path.join(app.getPath('temp'), 'rotkehlchen');
            if (!fs.existsSync(tempPath)) {
                fs.mkdirSync(tempPath)
            }
            args.push('--data-dir', tempPath)
        }
        pyProc = require('child_process').spawn('python', args);
    }

    pyProc.on('error', (err) => {
        console.error(err);
        console.log('Failed to start python subprocess.');
    });
    pyProc.on('exit', function (code, signal) {
        console.log("python subprocess killed with signal " + signal + " and code " + code);
        if (code !== 0) {
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
