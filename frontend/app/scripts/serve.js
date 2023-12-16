#!/usr/bin/env node

import { spawn } from 'node:child_process';
import process from 'node:process';
import { ArgumentParser } from 'argparse';
import electron from 'electron';
import { build, createLogger, createServer } from 'vite';
import { LOG_LEVEL, sharedConfig } from './setup.js';

const parser = new ArgumentParser({
  description: 'Rotki frontend build',
});
parser.add_argument('--web', { action: 'store_true' });
parser.add_argument('--remote-debugging-port', { type: 'int' });
parser.add_argument('--mode', { help: 'mode docker', default: 'development' });
parser.add_argument('--port', {
  help: 'listening port',
  default: 8080,
  type: 'int',
});
const args = parser.parse_args();
const { web, remote_debugging_port, mode, port } = args;

/** Messages on stderr that match any of the contained patterns will be stripped from output */
const stderrFilterPatterns = [
  // warning about devtools extension
  // https://github.com/cawa-93/vite-electron-builder/issues/492
  // https://github.com/MarshallOfSound/electron-devtools-installer/issues/143
  /ExtensionLoadWarning/,
];

/**
 * @param {{name: string; configFile: string; writeBundle: import('rollup').OutputPlugin['writeBundle'] }} param0
 */
function getWatcher({ name, configFile, writeBundle }) {
  return build({
    ...sharedConfig,
    mode,
    configFile,
    plugins: [{ name, writeBundle }],
  });
}

/** @type {ChildProcessWithoutNullStreams[]} */
let childProcesses = [];

/**
 * Start or restart App when source files are changed
 * @param {{config: {server: import('vite').ResolvedServerOptions}}} ResolvedServerOptions
 */
function setupMainPackageWatcher({ config: { server } }) {
  // Create VITE_DEV_SERVER_URL environment variable to pass it to the main process.
  const protocol = server.https ? 'https:' : 'http:';
  const host = server.host || 'localhost';
  const port = server.port; // Vite searches for and occupies the first free port: 3000, 3001, 3002 and so on
  const urlPath = '/';
  process.env.VITE_DEV_SERVER_URL = `${protocol}//${host}:${port}${urlPath}`;

  const logger = createLogger(LOG_LEVEL, {
    prefix: '[main]',
  });

  /** @type {ChildProcessWithoutNullStreams | null} */
  let spawnProcess = null;

  return getWatcher({
    name: 'reload-app-on-main-package-change',
    configFile: 'vite.config.main.ts',
    writeBundle() {
      if (spawnProcess) {
        childProcesses = childProcesses.filter(p => p !== spawnProcess);
        spawnProcess.off('exit', process.exit);
        spawnProcess.kill('SIGINT');
        spawnProcess = null;
      }

      const args = ['.'];
      if (remote_debugging_port)
        args.push(`--remote-debugging-port=${remote_debugging_port}`);

      if (process.env.XDG_SESSION_TYPE === 'wayland')
        args.push('--enable-features=WaylandWindowDecorations', '--ozone-platform-hint=auto');

      spawnProcess = spawn(String(electron), args);
      childProcesses.push(spawnProcess);

      spawnProcess.stdout.on('data', d => d.toString().trim() && logger.warn(d.toString(), { timestamp: true }));
      spawnProcess.stderr.on('data', (d) => {
        const data = d.toString().trim();
        if (!data)
          return;

        const mayIgnore = stderrFilterPatterns.some(r => r.test(data));
        if (mayIgnore)
          return;

        logger.error(data, { timestamp: true });
      });

      // Stops the watch script when the application has been quit
      spawnProcess.on('exit', process.exit);
    },
  });
}

/**
 * Start or restart App when source files are changed
 * @param {{ws: import('vite').WebSocketServer}} WebSocketServer
 */
function setupPreloadPackageWatcher({ ws }) {
  return getWatcher({
    name: 'reload-page-on-preload-package-change',
    configFile: 'vite.config.preload.ts',
    writeBundle() {
      ws.send({
        type: 'full-reload',
      });
    },
  });
}

async function serve() {
  try {
    const viteDevServer = await createServer({
      ...sharedConfig,
      mode: process.env.CI && process.env.VITE_TEST ? 'production' : mode,
      configFile: 'vite.config.ts',
      server: {
        port,
      },
    });

    await viteDevServer.listen();
    viteDevServer.printUrls();

    if (!web) {
      await setupPreloadPackageWatcher(viteDevServer);
      await setupMainPackageWatcher(viteDevServer);
    }

    process.on('SIGINT', () => {
      viteDevServer.close();
      childProcesses.forEach((p) => {
        console.info(`terminating child process ${p.pid}`);
        p.kill();
      });
      process.exit();
    });
  }
  catch (error) {
    console.error(error);
    process.exit(1);
  }
}

// re-evaluate after moving to mjs or ts
// eslint-disable-next-line unicorn/prefer-top-level-await
serve();
