#!/usr/bin/env node

const { spawn } = require('child_process');
const electron = require('electron');
const { createServer, build, createLogger } = require('vite');
const scriptArgs = process.argv;
const noElectron = scriptArgs.indexOf('--web') >= 0;
const { LOG_LEVEL, sharedConfig } = require('./setup');

/** Messages on stderr that match any of the contained patterns will be stripped from output */
const stderrFilterPatterns = [
  // warning about devtools extension
  // https://github.com/cawa-93/vite-electron-builder/issues/492
  // https://github.com/MarshallOfSound/electron-devtools-installer/issues/143
  /ExtensionLoadWarning/
];

/**
 * @param {{name: string; configFile: string; writeBundle: import('rollup').OutputPlugin['writeBundle'] }} param0
 */
const getWatcher = ({ name, configFile, writeBundle }) => {
  return build({
    ...sharedConfig,
    configFile,
    plugins: [{ name, writeBundle }]
  });
};

/**
 * Start or restart App when source files are changed
 * @param {{config: {server: import('vite').ResolvedServerOptions}}} ResolvedServerOptions
 */
const setupMainPackageWatcher = ({ config: { server } }) => {
  // Create VITE_DEV_SERVER_URL environment variable to pass it to the main process.
  const protocol = server.https ? 'https:' : 'http:';
  const host = server.host || 'localhost';
  const port = server.port; // Vite searches for and occupies the first free port: 3000, 3001, 3002 and so on
  const urlPath = '/';
  process.env.VITE_DEV_SERVER_URL = `${protocol}//${host}:${port}${urlPath}`;

  const logger = createLogger(LOG_LEVEL, {
    prefix: '[main]'
  });

  /** @type {ChildProcessWithoutNullStreams | null} */
  let spawnProcess = null;

  return getWatcher({
    name: 'reload-app-on-main-package-change',
    configFile: 'vite.config.main.ts',
    writeBundle() {
      if (spawnProcess) {
        spawnProcess.off('exit', process.exit);
        spawnProcess.kill('SIGINT');
        spawnProcess = null;
      }

      spawnProcess = spawn(String(electron), ['.']);

      spawnProcess.stdout.on(
        'data',
        d =>
          d.toString().trim() && logger.warn(d.toString(), { timestamp: true })
      );
      spawnProcess.stderr.on('data', d => {
        const data = d.toString().trim();
        if (!data) return;
        const mayIgnore = stderrFilterPatterns.some(r => r.test(data));
        if (mayIgnore) return;
        logger.error(data, { timestamp: true });
      });

      // Stops the watch script when the application has been quit
      spawnProcess.on('exit', process.exit);
    }
  });
};

/**
 * Start or restart App when source files are changed
 * @param {{ws: import('vite').WebSocketServer}} WebSocketServer
 */
const setupPreloadPackageWatcher = ({ ws }) =>
  getWatcher({
    name: 'reload-page-on-preload-package-change',
    configFile: 'vite.config.preload.ts',
    writeBundle() {
      ws.send({
        type: 'full-reload'
      });
    }
  });

(async () => {
  try {
    const viteDevServer = await createServer({
      ...sharedConfig,
      configFile: 'vite.config.ts'
    });

    await viteDevServer.listen();
    viteDevServer.printUrls();

    if (!noElectron) {
      await setupPreloadPackageWatcher(viteDevServer);
      await setupMainPackageWatcher(viteDevServer);
    }
  } catch (e) {
    console.error(e);
    process.exit(1);
  }
})();
