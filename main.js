const electron = require('electron');
const app = electron.app;
const Menu = electron.Menu;
const ipcMain = electron.ipcMain;
const BrowserWindow = electron.BrowserWindow;
const path = require('path');
const fs = require('fs');

let executable_name = null;
let to_kill_pids = null;

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

function setupInspectMenu() {
    if (process.env.ROTKEHLCHEN_ENVIRONMENT === 'development') {
        let rightClickPosition = null;

        const menu = new electron.Menu();
        const menuItem = new electron.MenuItem({
            label: 'Inspect Element',
            click: () => {
                mainWindow.inspectElement(rightClickPosition.x, rightClickPosition.y);
            }
        });

        menu.append(menuItem);

        mainWindow.webContents.on('context-menu', (e, params) => {
            e.preventDefault();
            rightClickPosition = {x: params.x, y: params.y};
            menu.popup(mainWindow);
        }, false);
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

    // open external links with default browser and not inside our electron app
    // https://stackoverflow.com/a/32427579/110395
    // Note for this to work anchor must have target="_blank"
    mainWindow.webContents.on('new-window', function(e, url) {
        e.preventDefault();
        electron.shell.openExternal(url);
    });

    // uncomment for the final app to have dev tools opened
    // mainWindow.webContents.openDevTools();

  // Check if we are on a MAC
    if (process.platform === 'darwin') {
        // Create our menu entries so that we can use MAC shortcuts
        Menu.setApplicationMenu(Menu.buildFromTemplate([
            {
                label: 'Edit',
                submenu: [
                    { role: 'undo' },
                    { role: 'redo' },
                    { type: 'separator' },
                    { role: 'cut' },
                    { role: 'copy' },
                    { role: 'paste' },
                    { role: 'pasteandmatchstyle' },
                    { role: 'delete' },
                    { role: 'selectall' }
                ]
            }
        ]));
    }

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    setupInspectMenu();
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

    let args = [];
    // try to see if there is a configfile
    if (fs.existsSync('rotki_config.json')) {
        let raw_data = fs.readFileSync('rotki_config.json');
        let no_errors = true;
        try {
            let jsondata = JSON.parse(raw_data);
            if (jsondata.hasOwnProperty('loglevel')) {
                args.push('--loglevel', jsondata['loglevel']);
            }
            if (jsondata.hasOwnProperty('logfromothermodules')) {
                if (jsondata['logfromothermodules'] == true) {
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
        } catch(e) {
            // do nothing, act as if there is no config given
            // TODO: Perhaps in the future warn the user inside
            // the app that there is a config file with invalid json
            console.log(`Could not read the rotki_config.json file due to: "${e}". Proceeding normally without a config file ....`);
        }

    }

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
	executable_name = executable;
	executable = path.join(dist_dir, executable);
        args.push("--zerorpc-port", port);
        console.log('Calling python backend with: ' + executable + ' ' + args.join(' '));
        pyProc = require('child_process').execFile(executable, args);
    } else {
        args.unshift("-m", "rotkehlchen");
        args.push("--zerorpc-port", port);

        if (process.env.ROTKEHLCHEN_ENVIRONMENT === 'test') {
            let tempPath = path.join(app.getPath('temp'), 'rotkehlchen');
            if (!fs.existsSync(tempPath)) {
                fs.mkdirSync(tempPath);
            }
            args.push('--data-dir', tempPath);
        }
        console.log('Calling python backend with: python ' + args.join(' '));
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

const exitPyProc = (event) => {
    console.log("KILLING PYPROCESS");
    if (process.platform === 'win32') {
	// For win32 we got two problems:
	// 1. pyProc.kill() does not work due to SIGTERM not really being a signal
	//    in Windows
	// 2. the onefile pyinstaller packaging creates two executables.
	// https://github.com/pyinstaller/pyinstaller/issues/2483
	// 
	// So the solution is to not let the application close, get all
	// pids and kill them before we close the app
	const tasklist = require('tasklist');
	console.log('Detecting Windows pids');
	tasklist().then(function(tasks){
	    console.log('In tasklist result for executable_name: ' + executable_name);
	    to_kill_pids = [];
	    for (var i = 0; i < tasks.length; i++) {
		if (tasks[i]['imageName'] === executable_name) {
		    to_kill_pids.push(tasks[i]['pid']);
		    console.log('adding pid ' + tasks[i]['pid']);
		}
	    }

	    // now that we have all the pids gathered, call taskkill on them
	    console.log('Calling taskkill for Windows pids');
	    var spawn = require('child_process').spawn;
	    args = ['/f', '/t'];
	    for (var i = 0; i < to_kill_pids.length; i++) {
		args.push('/PID');
		args.push(to_kill_pids[i]);
	    }
	    console.log('command is: taskkill and args: ' + JSON.stringify(args, null, 4));
	    killProc = spawn('taskkill', args);
	    killProc.on('exit', function (code, signal) {
		console.log("Kill proc on exit");
		app.exit();
	    });
	    killProc.on('error', (err) => {
		console.error("Kill proc on error:" + err);
		app.exit();
	    });
	});

	pyProc.kill();
	// Do not allow the app to quit. Instead wait for killProc to occur
	// which will quit the app itself.
	event.preventDefault();
    } else {
	pyProc.kill();
    }
    pyProc = null;
    pyPort = null;
};

app.on('ready', createPyProc);
app.on('will-quit', exitPyProc);
