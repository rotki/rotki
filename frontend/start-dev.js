const fs = require("fs");
const { spawn } = require("child_process");

if (!process.env.VIRTUAL_ENV) {
  process.stdout.write("No python virtual environment detected\n");
  process.exit(1);
}

let startDevProxy = false;
const devEnvExists = fs.existsSync("app/.env.development.local");
if (devEnvExists) {
  require("dotenv").config({ path: "app/.env.development.local" });
  startDevProxy = !!process.env.VUE_APP_BACKEND_URL;
}

console.log(startDevProxy);

const subprocesses = [];

process.on("beforeExit", () => {
  process.stdout.write("preparing to terminate subprocesses");
  for (const subprocess of subprocesses) {
    subprocess.kill();
  }
});

if (startDevProxy) {
  process.stdout.write("Starting dev-proxy \n");
  const devProxyProcess = spawn("npm run serve", {
    cwd: "./dev-proxy",
    shell: true,
    stdio: [process.stdin, process.stdout, process.stderr]
  });
  subprocesses.push(devProxyProcess);
}

process.stdout.write("Starting @rotki/common watch \n");
const commonProcesses = spawn("sleep 30 && npm run watch -w @rotki/common", {
  shell: true,
  stdio: [process.stdin, process.stdout, process.stderr]
});
process.stdout.write("Starting rotki dev mode \n");
const devRotkiProcess = spawn("npm run electron:serve -w rotki", {
  shell: true,
  stdio: [process.stdin, process.stdout, process.stderr]
});
subprocesses.push(commonProcesses, devRotkiProcess);

