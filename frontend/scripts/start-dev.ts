import { type ChildProcess, execSync, spawn } from 'node:child_process';
import process, { exit } from 'node:process';
import fs from 'node:fs';
import { platform } from 'node:os';
import path from 'node:path';
import net from 'node:net';
import { config } from 'dotenv';
import consola from 'consola';
import { assert } from '@rotki/common';
import { omit } from 'es-toolkit';
import type { Buffer } from 'node:buffer';

interface OutputListener {
  out: (buffer: Buffer) => void;
  err: (buffer: Buffer) => void;
}

const DEFAULT_BACKEND_PORT = 4242;
const DEFAULT_COLIBRI_PORT = 4343;

const PROXY = 'proxy';
const COMMON = '@rotki/common';
const ROTKI = 'rotki';
const BACKEND = 'backend';
const COLIBRI = 'colibri';

const scriptArgs = process.argv;
const noElectron = scriptArgs.includes('--web');

const webPort = getPort('--web-port', DEFAULT_BACKEND_PORT);
const colibriPort = getPort('--colibri-port', DEFAULT_COLIBRI_PORT);

function getPort(arg: string, defaultValue: number): number {
  const portValue = getArg(arg);
  if (!portValue) {
    return defaultValue;
  }
  const portNumber = Number.parseInt(portValue);
  if (!isFinite(portNumber) || portNumber < 0 || portNumber > 65535) {
    return defaultValue;
  }
  return portNumber;
}

async function isPortAvailable(port: number): Promise<boolean> {
  return new Promise<boolean>((resolve, reject) => {
    const server = net.createServer();

    server.unref();

    server.once('error', (err: any) => {
      if (err.code === 'EADDRINUSE' || err.code === 'EACCES')
        resolve(false);
      else
        reject(err instanceof Error ? err : new Error(err));
    });

    server.once('listening', () => {
      server.close(() => resolve(true));
    });

    server.listen(port, '127.0.0.1');
  });
}

export async function selectPort(startPort: number): Promise<number> {
  for (let portNumber = startPort; portNumber <= 65535; portNumber++) {
    if (await isPortAvailable(portNumber))
      return portNumber;
  }
  throw new Error('no free ports found');
}

function getArg(flag: string): string | undefined {
  if (scriptArgs.includes(flag) && scriptArgs.length > scriptArgs.indexOf(flag) + 1)
    return scriptArgs[scriptArgs.indexOf(flag) + 1];
}

function checkForCargo(): boolean {
  try {
    const cargoVersion = execSync('cargo --version', { encoding: 'utf-8' });
    consola.info(`detected cargo: ${cargoVersion}`);
    return /cargo\s\d+\.\d+\.\d+/.test(cargoVersion);
  }
  catch {
    consola.error('Cargo is not installed');
    return false;
  }
}

const profilingArgs = getArg('--profiling-args');
const profilingCmd = getArg('--profiling-cmd');

if (profilingCmd)
  process.env.ROTKI_BACKEND_PROFILING_CMD = profilingCmd;

if (profilingArgs)
  process.env.ROTKI_BACKEND_PROFILING_ARGS = profilingArgs;

const colors = {
  red: (msg: string) => `\u001B[31m${msg}\u001B[0m`,
  green: (msg: string) => `\u001B[32m${msg}\u001B[0m`,
  yellow: (msg: string) => `\u001B[33m${msg}\u001B[0m`,
  blue: (msg: string) => `\u001B[34m${msg}\u001B[0m`,
  magenta: (msg: string) => `\u001B[35m${msg}\u001B[0m`,
  cyan: (msg: string) => `\u001B[36m${msg}\u001B[0m`,
} as const;

const logger = consola.withTag(colors.cyan('dev'));

if (!process.env.VIRTUAL_ENV) {
  logger.info('No python virtual environment detected');
  process.exit(1);
}

const cargoInstalled = checkForCargo();
if (cargoInstalled) {
  consola.info('Cargo is installed building colibri binary');
  execSync('cargo build', {
    encoding: 'utf-8',
    cwd: path.join('..', 'colibri'),
    stdio: 'inherit',
  });
}

let startDevProxy = false;
const devEnvExists = fs.existsSync('app/.env.development.local');
if (devEnvExists) {
  config({ path: 'app/.env.development.local' });
  startDevProxy = !!process.env.VITE_BACKEND_URL;
}

const pids: Record<number, string> = {};
const listeners: Record<number, OutputListener> = {};
const subprocesses: ChildProcess[] = [];

function startProcess(
  cmd: string,
  tag: string,
  name: string,
  args: string[] = [],
  opts: Record<string, any> = {},
): ChildProcess {
  const logger = consola.withTag(tag);
  const createListeners = (): OutputListener => ({
    out: (buffer: Buffer): void => {
      logger.log(buffer.toString().replace(/\n$/, ''));
    },
    err: (buffer: Buffer): void => {
      logger.log(buffer.toString().replace(/\n$/, ''));
    },
  });

  const envVars = opts?.env ?? {};
  const env = {
    FORCE_COLOR: '1',
    ...process.env,
    NODE_ENV: 'development',
    ...envVars,
  };

  const child = spawn(cmd, args, {
    ...omit(opts, ['env']),
    shell: true,
    stdio: [process.stdin],
    env,
  });

  subprocesses.push(child);

  const stdListeners = createListeners();
  child.stdout?.on('data', stdListeners.out);
  child.stderr?.on('data', stdListeners.err);
  const pid = child.pid;
  assert(pid !== undefined, 'pid is undefined');
  pids[pid] = name;
  listeners[pid] = stdListeners;
  return child;
}

function terminateSubprocesses() {
  let subprocess;
  // eslint-disable-next-line no-cond-assign
  while ((subprocess = subprocesses.pop())) {
    if (subprocess.killed)
      continue;

    const pid = subprocess.pid;
    if (pid === undefined) {
      continue;
    }

    const name = pids[pid] ?? '';
    logger.info(`terminating process: ${name} (${pid})`);
    const ls = listeners[pid];
    if (ls) {
      subprocess.stdout?.off('data', ls.out);
      subprocess.stderr?.off('data', ls.err);
      delete listeners[pid];
    }

    subprocess.kill();
  }
}

process.on('SIGINT', () => {
  logger.info(`preparing to terminate subprocesses`);
  terminateSubprocesses();
  exit(0);
});

if (startDevProxy) {
  logger.info('Starting dev-proxy');
  startProcess('pnpm run --filter @rotki/dev-proxy serve', colors.green(PROXY), PROXY);
}

logger.info('Starting @rotki/common watch');

startProcess('pnpm run --filter @rotki/common watch', colors.blue(COMMON), COMMON);

let backendEnv: {
  VITE_BACKEND_URL: string;
  VITE_COLIBRI_URL: string;
} | undefined;

if (noElectron) {
  const availableWebPort = await selectPort(webPort);
  logger.info(`Starting python backend at port: ${availableWebPort}`);

  const logDir = path.join(process.cwd(), 'logs');
  if (!fs.existsSync(logDir))
    fs.mkdirSync(logDir);

  const args = [
    ...(profilingArgs ? profilingArgs.split(' ') : []),
    ...(profilingCmd ? ['python'] : []),
    '-m',
    'rotkehlchen',
    '--rest-api-port',
    availableWebPort.toString(),
    '--api-cors',
    'http://localhost:*',
    '--logfile',
    `${path.join(logDir, 'backend.log')}`,
  ];

  startProcess(profilingCmd ?? 'python', colors.yellow(BACKEND), BACKEND, args, {
    cwd: path.join('..'),
  });

  const availableColibriPort = await selectPort(colibriPort);

  logger.info(`Starting colibri at port: ${availableColibriPort}`);

  const colibriArgs: string[] = [
    `--logfile-path=${path.join(logDir, 'colibri.log')}`,
    `--port=${availableColibriPort}`,
  ];

  startProcess('cargo run -- ', colors.red(COLIBRI), COLIBRI, colibriArgs, {
    cwd: path.join('..', 'colibri'),
  });

  backendEnv = {
    VITE_BACKEND_URL: `http://localhost:${availableWebPort}`,
    VITE_COLIBRI_URL: `http://localhost:${availableColibriPort}`,
  };
}

logger.info('Starting rotki dev mode');

function getDebuggerPort() {
  try {
    const debuggerPort = process.env.DEBUGGER_PORT;
    if (debuggerPort) {
      const portNum = Number.parseInt(debuggerPort);
      return isFinite(portNum) && (portNum > 0 || portNum < 65535) ? portNum : null;
    }
    return null;
  }
  catch {
    return null;
  }
}
const debuggerPort = getDebuggerPort();
const args = debuggerPort ? ` --remote-debugging-port=${debuggerPort}` : '';
if (args)
  logger.info(`starting rotki with args: ${args}`);

const serveCmd = noElectron ? 'pnpm run --filter rotki serve' : 'pnpm run --filter rotki electron:serve';
const cmd = platform() === 'win32' ? serveCmd : `sleep 20 && ${serveCmd}`;

const devRotkiProcess = startProcess(`${cmd} ${args}`, colors.magenta(ROTKI), ROTKI, [], {
  env: backendEnv,
});

devRotkiProcess.on('exit', () => {
  logger.info('dev rotki process exited, terminating subprocesses');
  terminateSubprocesses();
  process.exit(0);
});
