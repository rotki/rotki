const electron = require('electron');
const app = electron.app;
const BrowserWindow = electron.BrowserWindow;
const path = require('path');


/*************************************************************
 * py process
 *************************************************************/

const PY_DIST_FOLDER = 'NOTAPPPLICABLE';
const PY_FOLDER = 'rotkelchen';
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

const createPyProc = () => {
    let script = getScriptPath();
    let port = '' + selectPort();

    if (guessPackaged()) {
	console.log("At guess packaged");
	pyProc = require('child_process').execFile(script, [port]);
    } else {
	console.log("At not packaged: script:" + script + " port: " + port);
	pyProc = require('child_process').spawn('python', [script, "--zerorpc-port", port]);
    }

    pyProc.on('error', (err) => {
	console.log('Failed to start python subprocess.');
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
