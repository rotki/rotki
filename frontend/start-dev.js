const { spawn } = require("child_process");
const fs = require("fs");

const PROXY = 'proxy';
const COMMON = '@rotki/common'
const ROTKI = 'rotki'

const colors = {
  magenta: (msg) => `\x1b[35m${msg}\x1b[0m`,
  green: (msg) => `\x1b[32m${msg}\x1b[0m`,
  blue: (msg) => `\x1b[34m${msg}\x1b[0m`,
  cyan: (msg) => `\x1b[36m${msg}\x1b[0m`
}

const logger = {
  info: (msg) => console.info(colors.cyan('dev'),`${msg}`),
  error: (prefix, msg) => console.error(prefix, msg.replace(/\n$/, "")),
  debug: (prefix, msg) => console.log(prefix, msg.replace(/\n$/, "")),
}

const pids = {}

if (!process.env.VIRTUAL_ENV) {
  logger.info("No python virtual environment detected");
  process.exit(1);
}

let startDevProxy = false;
const devEnvExists = fs.existsSync("app/.env.development.local");
if (devEnvExists) {
  require("dotenv").config({ path: "app/.env.development.local" });
  startDevProxy = !!process.env.VUE_APP_BACKEND_URL;
}

const subprocesses = [];

const terminateSubprocesses = () => {
  let subprocess
  while(subprocess = subprocesses.pop()) {
    if (subprocess.killed) {
      continue
    }
    const name = pids[subprocess.pid] ?? '';
    logger.info(`terminating process: ${name} (${subprocess.pid})`);
    subprocess.kill('SIGTERM');
  }
};
process.on("beforeExit", terminateSubprocesses);

if (startDevProxy) {
  logger.info("Starting dev-proxy");
  const devProxyProcess = spawn("npm run serve", {
    cwd: "./dev-proxy",
    shell: true,
    stdio: [process.stdin]
  });
  subprocesses.push(devProxyProcess);

  devProxyProcess.stdout.on('data', buffer  => {
    logger.debug(colors.green(PROXY), buffer.toLocaleString())
  })
  devProxyProcess.stderr.on('data', buffer => {
    logger.error(colors.green(PROXY), buffer.toLocaleString())
  })
  pids[devProxyProcess.pid] = PROXY
}

logger.info("Starting @rotki/common watch");
const commonProcesses = spawn("npm run watch -w @rotki/common", {
  shell: true,
  stdio: [process.stdin]
});
commonProcesses.stdout.on('data', buffer  => {
  logger.debug(colors.blue(COMMON), buffer.toLocaleString())
})
commonProcesses.stderr.on('data', buffer => {
  logger.error(colors.blue(COMMON), buffer.toLocaleString())
})

pids[commonProcesses.pid] = COMMON

logger.info("Starting rotki dev mode");
const getDebuggerPort = () => {
  try {
    const debuggerPort = process.env.DEBUGGER_PORT;
    if (debuggerPort) {
      const portNum = parseInt(debuggerPort);
      return isFinite(portNum) && (portNum > 0 || portNum < 65535) ? portNum : null;
    }
    return null
  } catch (e) {
    return null
  }
};
const debuggerPort = getDebuggerPort()
const args = debuggerPort? ` -- --remote-debugging-port=${debuggerPort}` : ''
if (args) {
  logger.info(`starting rotki with args: ${args}`)
}
const devRotkiProcess = spawn(`sleep 20 && npm run electron:serve -w rotki${args}`, {
  shell: true,
  stdio: [process.stdin]
});

devRotkiProcess.stdout.on('data', buffer  => {
  logger.debug(colors.magenta(ROTKI), buffer.toLocaleString())
})
devRotkiProcess.stderr.on('data', buffer => {
  logger.error(colors.magenta(ROTKI), buffer.toLocaleString())
})

pids[devRotkiProcess.pid] = ROTKI

devRotkiProcess.on('exit', () => {
  terminateSubprocesses()
  process.exit(0)
})

subprocesses.push(commonProcesses, devRotkiProcess);

