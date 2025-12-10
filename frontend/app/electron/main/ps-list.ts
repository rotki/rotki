/**
 * https://raw.githubusercontent.com/sindresorhus/ps-list/refs/heads/main/index.js
 */

import childProcess from 'node:child_process';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));

const TEN_MEGABYTES = 1000 * 1000 * 10;
const execFile = promisify(childProcess.execFile);

interface Options {
  /**
   Include other users' processes as well as your own.

   On Windows this has no effect and will always be the users' own processes.

   @default true
   */
  readonly all?: boolean;
}

export interface ProcessDescriptor {
  readonly pid: number;
  readonly name: string;
  readonly ppid: number;

  /**
   Not supported on Windows.
   */
  readonly cmd?: string;

  /**
   Not supported on Windows.
   */
  readonly cpu?: number;

  /**
   Not supported on Windows.
   */
  readonly memory?: number;

  /**
   Not supported on Windows.
   */
  readonly uid?: number;
}

async function windows(): Promise<ProcessDescriptor[]> {
  // Source: https://github.com/MarkTiedemann/fastlist
  let binary;
  if (process.arch === 'x64') {
    binary = 'fastlist-0.3.0-x64.exe';
  }
  else if (process.arch === 'ia32') {
    binary = 'fastlist-0.3.0-x86.exe';
  }
  else {
    throw new Error(`Unsupported architecture: ${process.arch}`);
  }

  const basePath = process.resourcesPath ? process.resourcesPath : currentDirectory;
  const binaryPath = path.join(basePath, 'vendor', binary);
  const { stdout } = await execFile(binaryPath, {
    maxBuffer: TEN_MEGABYTES,
    windowsHide: true,
  });

  return stdout
    .trim()
    .split('\r\n')
    .map(line => line.split('\t'))
    .map(([pid, ppid, name]) => ({
      pid: Number.parseInt(pid, 10),
      ppid: Number.parseInt(ppid, 10),
      name,
    }));
}

async function nonWindowsMultipleCalls(options: Options = {}): Promise<ProcessDescriptor[]> {
  const flags = `${options.all === false ? '' : 'a'}wwxo`;
  const returnValue: Record<string, Record<string, string>> = {};

  await Promise.all(['comm', 'args', 'ppid', 'uid', '%cpu', '%mem'].map(async (cmd) => {
    const { stdout } = await execFile('ps', [flags, `pid,${cmd}`], { maxBuffer: TEN_MEGABYTES });

    for (let line of stdout.trim().split('\n').slice(1)) {
      line = line.trim();
      const [pid] = line.split(' ', 1);
      const value = line.slice(pid.length + 1).trim();

      if (returnValue[pid] === undefined)
        returnValue[pid] = {};

      returnValue[pid][cmd] = value;
    }
  }));

  // Filter out inconsistencies as there might be race
  // issues due to differences in `ps` between the spawns
  return Object.entries(returnValue)
    .filter(([, value]) => value.comm && value.args && value.ppid && value.uid && value['%cpu'] && value['%mem'])
    .map(([key, value]) => ({
      pid: Number.parseInt(key, 10),
      name: path.basename(value.comm),
      cmd: value.args,
      ppid: Number.parseInt(value.ppid, 10),
      uid: Number.parseInt(value.uid, 10),
      cpu: Number.parseFloat(value['%cpu']),
      memory: Number.parseFloat(value['%mem']),
    }));
}

const ERROR_MESSAGE_PARSING_FAILED = 'ps output parsing failed';

const psOutputRegex = /^[\t ]*(?<pid>\d+)[\t ]+(?<ppid>\d+)[\t ]+(?<uid>[\d-]+)[\t ]+(?<cpu>\d+\.\d+)[\t ]+(?<memory>\d+\.\d+)[\t ]+(?<comm>.*)?/;

async function nonWindowsCall(options: Options = {}): Promise<ProcessDescriptor[]> {
  const flags = options.all === false ? 'wwxo' : 'awwxo';

  const psPromises = [
    execFile('ps', [flags, 'pid,ppid,uid,%cpu,%mem,comm'], { maxBuffer: TEN_MEGABYTES }),
    execFile('ps', [flags, 'pid,args'], { maxBuffer: TEN_MEGABYTES }),
  ];

  const [psLines, psArgsLines] = (await Promise.all(psPromises)).map(({ stdout }) => stdout.trim().split('\n'));

  const psPids = new Set(psPromises.map(promise => promise.child.pid));

  psLines.shift();
  psArgsLines.shift();

  const processCmds: Record<string, string> = {};
  for (const line of psArgsLines) {
    const [pid, ...cmds] = line.trim().split(' ');
    processCmds[pid] = cmds.join(' ');
  }

  return psLines.map((line) => {
    const match = psOutputRegex.exec(line);

    if (match === null)
      throw new Error(ERROR_MESSAGE_PARSING_FAILED);

    const groups = match.groups;
    if (!groups)
      throw new Error('groups was undefined');

    return {
      pid: Number.parseInt(groups.pid, 10),
      ppid: Number.parseInt(groups.ppid, 10),
      uid: Number.parseInt(groups.uid, 10),
      cpu: Number.parseFloat(groups.cpu),
      memory: Number.parseFloat(groups.memory),
      name: path.basename(groups.comm),
      cmd: processCmds[groups.pid],
    };
  }).filter(processInfo => !psPids.has(processInfo.pid));
}

async function nonWindows(options: Options = {}): Promise<ProcessDescriptor[]> {
  try {
    return await nonWindowsCall(options);
  }
  catch { // If the error is not a parsing error, it should manifest itself in multicall version too.
    return nonWindowsMultipleCalls(options);
  }
}

/**
 Get running processes.

 @returns A list of running processes.

 @example
 ```
 import psList from 'ps-list';

 console.log(await psList());
 //=> [{pid: 3213, name: 'node', cmd: 'node test.js', ppid: 1, uid: 501, cpu: 0.1, memory: 1.5}, …]
 ```
 */
export const psList = process.platform === 'win32' ? windows : nonWindows;
