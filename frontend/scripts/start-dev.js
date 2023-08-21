const { spawn } = require('node:child_process');
const fs = require('node:fs');
const { platform } = require('node:os');
const path = require('node:path');
const { exit } = require('node:process');

const PROXY = 'proxy';
const COMMON = '@rotki/common';
const ROTKI = 'rotki';
const BACKEND = 'backend';

const scriptArgs = process.argv;
const noElectron = scriptArgs.includes('--web');

const colors = {
  magenta: msg => `\u001B[35m${msg}\u001B[0m`,
  green: msg => `\u001B[32m${msg}\u001B[0m`,
  yellow: msg => `\u001B[33m${msg}\u001B[0m`,
  blue: msg => `\u001B[34m${msg}\u001B[0m`,
  cyan: msg => `\u001B[36m${msg}\u001B[0m`
};

const logger = {
  info: msg => console.info(colors.cyan('dev'), `${msg}`),
  error: (prefix, msg) => console.error(prefix, msg.replace(/\n$/, '')),
  debug: (prefix, msg) => console.log(prefix, msg.replace(/\n$/, ''))
};

if (!process.env.VIRTUAL_ENV) {
  logger.info('No python virtual environment detected');
  process.exit(1);
}

let startDevProxy = false;
const devEnvExists = fs.existsSync('app/.env.development.local');
if (devEnvExists) {
  require('dotenv').config({ path: 'app/.env.development.local' });
  startDevProxy = !!process.env.VITE_BACKEND_URL;
}

const pids = {};
const listeners = {};
const subprocesses = [];

const startProcess = (cmd, tag, name, args, opts = undefined) => {
  const createListeners = tag => ({
    out: buffer => {
      logger.debug(tag, buffer.toLocaleString());
    },
    err: buffer => {
      logger.error(tag, buffer.toLocaleString());
    }
  });

  const child = spawn(cmd, args, {
    ...opts,
    shell: true,
    stdio: [process.stdin]
  });

  subprocesses.push(child);

  const stdListeners = createListeners(tag);
  child.stdout.on('data', stdListeners.out);
  child.stderr.on('data', stdListeners.err);
  pids[child.pid] = name;
  listeners[child.pid] = stdListeners;
  return child;
};

const terminateSubprocesses = () => {
  let subprocess;
  while ((subprocess = subprocesses.pop())) {
    if (subprocess.killed) {
      continue;
    }
    const name = pids[subprocess.pid] ?? '';
    logger.info(`terminating process: ${name} (${subprocess.pid})`);
    const ls = listeners[subprocess.pid];
    if (ls) {
      subprocess.stdout.off('data', ls.out);
      subprocess.stderr.off('data', ls.err);
      delete listeners[subprocess.pid];
    }

    subprocess.kill();
  }
};

process.on('SIGINT', () => {
  logger.info(`preparing to terminate subprocesses`);
  terminateSubprocesses();
  exit(0);
});

if (startDevProxy) {
  logger.info('Starting dev-proxy');
  startProcess(
    'pnpm run --filter @rotki/dev-proxy serve',
    colors.green(PROXY),
    PROXY
  );
}

logger.info('Starting @rotki/common watch');

startProcess(
  'pnpm run --filter @rotki/common watch',
  colors.blue(COMMON),
  COMMON
);

if (noElectron) {
  logger.info('Starting python backend');
  const logDir = path.join(process.cwd(), 'logs');
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir);
  }

  const args = [
    '-m',
    'rotkehlchen',
    '--rest-api-port',
    '4242',
    '--api-cors',
    'http://localhost:*',
    '--logfile',
    `${path.join(logDir, 'backend.log')}`
  ];

  startProcess('python', colors.yellow(BACKEND), BACKEND, args, {
    cwd: path.join('..')
  });
}

logger.info('Starting rotki dev mode');
const getDebuggerPort = () => {
  try {
    const debuggerPort = process.env.DEBUGGER_PORT;
    if (debuggerPort) {
      const portNum = Number.parseInt(debuggerPort);
      return isFinite(portNum) && (portNum > 0 || portNum < 65535)
        ? portNum
        : null;
    }
    return null;
  } catch {
    return null;
  }
};
const debuggerPort = getDebuggerPort();
const args = debuggerPort ? ` --remote-debugging-port=${debuggerPort}` : '';
if (args) {
  logger.info(`starting rotki with args: ${args}`);
}

const serveCmd = noElectron
  ? 'pnpm run --filter rotki serve'
  : 'pnpm run --filter rotki electron:serve';
const cmd = platform() === 'win32' ? serveCmd : `sleep 20 && ${serveCmd}`;

const devRotkiProcess = startProcess(
  `${cmd} ${args}`,
  colors.magenta(ROTKI),
  ROTKI
);

devRotkiProcess.on('exit', () => {
  terminateSubprocesses();
});
