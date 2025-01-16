import { type ChildProcess, execSync, spawn } from 'node:child_process';
import process, { exit } from 'node:process';
import fs from 'node:fs';
import { platform } from 'node:os';
import path from 'node:path';
import { config } from 'dotenv';
import consola from 'consola';
import { assert } from '@rotki/common';
import type { Buffer } from 'node:buffer';

interface OutputListener {
  out: (buffer: Buffer) => void;
  err: (buffer: Buffer) => void;
}

const PROXY = 'proxy';
const COMMON = '@rotki/common';
const ROTKI = 'rotki';
const BACKEND = 'backend';

const scriptArgs = process.argv;
const noElectron = scriptArgs.includes('--web');

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
  magenta: (msg: string) => `\u001B[35m${msg}\u001B[0m`,
  green: (msg: string) => `\u001B[32m${msg}\u001B[0m`,
  yellow: (msg: string) => `\u001B[33m${msg}\u001B[0m`,
  blue: (msg: string) => `\u001B[34m${msg}\u001B[0m`,
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
  opts?: Record<string, any>,
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

  const child = spawn(cmd, args, {
    ...opts,
    shell: true,
    stdio: [process.stdin],
    env: {
      ...{ FORCE_COLOR: '1' },
      ...process.env,
    },
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

if (noElectron) {
  logger.info('Starting python backend');
  const logDir = path.join(process.cwd(), 'logs');
  if (!fs.existsSync(logDir))
    fs.mkdirSync(logDir);

  const args = [
    ...(profilingArgs ? profilingArgs.split(' ') : []),
    ...(profilingCmd ? ['python'] : []),
    '-m',
    'rotkehlchen',
    '--rest-api-port',
    '4242',
    '--api-cors',
    'http://localhost:*',
    '--logfile',
    `${path.join(logDir, 'backend.log')}`,
  ];

  startProcess(profilingCmd ?? 'python', colors.yellow(BACKEND), BACKEND, args, {
    cwd: path.join('..'),
  });
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

const devRotkiProcess = startProcess(`${cmd} ${args}`, colors.magenta(ROTKI), ROTKI);

devRotkiProcess.on('exit', () => {
  terminateSubprocesses();
});
