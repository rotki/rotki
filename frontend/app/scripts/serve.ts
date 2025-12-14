#!/usr/bin/env node

import type { OutputPlugin } from 'rollup';
import { type ChildProcessWithoutNullStreams, spawn } from 'node:child_process';
import process from 'node:process';
import { cac } from 'cac';
import consola from 'consola';
import electron from 'electron';
import { build, createLogger, createServer, type ViteDevServer } from 'vite';
import { type BuildOutput, LOG_LEVEL, sharedConfig } from './setup';

/** Messages on stderr that match any of the contained patterns will be stripped from output */
const stderrFilterPatterns = [
  // warning about devtools extension
  // https://github.com/cawa-93/vite-electron-builder/issues/492
  // https://github.com/MarshallOfSound/electron-devtools-installer/issues/143
  /ExtensionLoadWarning/,
];

interface WatcherConfig {
  name: string;
  configFile: string;
  writeBundle: OutputPlugin['writeBundle'];
}

interface ServeOptions {
  web: boolean;
  remoteDebuggingPort?: number;
  mode: string;
  port: number;
}

async function getWatcher({ name, configFile, writeBundle }: WatcherConfig, mode: string): Promise<BuildOutput> {
  return build({
    ...sharedConfig,
    mode,
    configFile,
    plugins: [{ name, writeBundle }],
  });
}

let childProcesses: ChildProcessWithoutNullStreams[] = [];

/**
 * Start or restart App when source files are changed
 */
async function setupMainPackageWatcher({ config: { server } }: ViteDevServer, mode: string, remoteDebuggingPort?: number): Promise<BuildOutput> {
  // Create VITE_DEV_SERVER_URL environment variable to pass it to the main process.
  const protocol = server.https ? 'https:' : 'http:';
  const host = server.host || 'localhost';
  const port = server.port; // Vite searches for and occupies the first free port: 3000, 3001, 3002, and so on
  const urlPath = '/';
  process.env.VITE_DEV_SERVER_URL = `${protocol}//${host}:${port}${urlPath}`;

  const logger = createLogger(LOG_LEVEL, {
    prefix: '[main]',
  });

  let spawnProcess: ChildProcessWithoutNullStreams | null = null;

  return getWatcher({
    name: 'reload-app-on-main-package-change',
    configFile: 'vite.config.main.ts',
    writeBundle() {
      if (spawnProcess) {
        childProcesses = childProcesses.filter(p => p !== spawnProcess);
        spawnProcess.off('exit', () => process.exit());
        spawnProcess.kill('SIGINT');
        spawnProcess = null;
      }

      const args = ['.'];
      if (remoteDebuggingPort)
        args.push(`--remote-debugging-port=${remoteDebuggingPort}`);

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
      spawnProcess.on('exit', () => process.exit());
    },
  }, mode);
}

/**
 * Start or restart App when source files are changed
 */
async function setupPreloadPackageWatcher({ ws }: ViteDevServer, mode: string): Promise<BuildOutput> {
  return getWatcher({
    name: 'reload-page-on-preload-package-change',
    configFile: 'vite.config.preload.ts',
    writeBundle() {
      ws.send({
        type: 'full-reload',
      });
    },
  }, mode);
}

async function serve(options: ServeOptions): Promise<void> {
  const { web, remoteDebuggingPort, mode, port } = options;

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
      await setupPreloadPackageWatcher(viteDevServer, mode);
      await setupMainPackageWatcher(viteDevServer, mode, remoteDebuggingPort);
    }

    const cleanup = (signal: string): void => {
      consola.info(`Received ${signal}, cleaning up...`);
      viteDevServer.close().then(() => {
        consola.info('Vite server stopped');
      }).catch(error => consola.error(error)).finally(() => {
        childProcesses.forEach((p) => {
          console.info(`terminating child process ${p.pid}`);
          p.kill();
        });
        process.exit();
      });
    };

    process.on('SIGINT', () => cleanup('SIGINT'));
    process.on('SIGTERM', () => cleanup('SIGTERM'));
    process.on('SIGHUP', () => cleanup('SIGHUP'));
  }
  catch (error) {
    consola.error(error);
    process.exit(1);
  }
}

const cli = cac();

cli.command('', 'Rotki frontend development server')
  .option('--web', 'Run as web-only (no Electron)')
  .option('--remote-debugging-port <port>', 'Chrome remote debugging port')
  .option('--mode <mode>', 'Development mode', { default: 'development' })
  .option('--port <port>', 'Listening port', { default: 8080 })
  .action(async (options) => {
    await serve({
      web: options.web ?? false,
      remoteDebuggingPort: options.remoteDebuggingPort ? Number(options.remoteDebuggingPort) : undefined,
      mode: options.mode,
      port: Number(options.port),
    });
  });

cli.help();
cli.parse();
