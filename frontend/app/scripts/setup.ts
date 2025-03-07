import type { RollupOutput, RollupWatcher } from 'rollup';
import type { InlineConfig, LogLevel } from 'vite';
import path from 'node:path';
import process from 'node:process';

export type BuildOutput = RollupOutput | RollupOutput[] | RollupWatcher;

export const mode: 'production' | 'development' = (process.env.NODE_ENV = process.env.NODE_ENV !== 'development' ? 'production' : 'development');

export const LOG_LEVEL: LogLevel = 'info';

export const sharedConfig: InlineConfig = {
  mode,
  logLevel: LOG_LEVEL,
};

// in some systems the virtualenv's python is not detected from inside electron and the
// system python is used. Electron/node seemed to add /usr/bin to the path before the
// virtualenv directory and as such system's python is used. Not sure why this happens only
// in some systems. Check again in the future if this happens in Lefteris laptop Archlinux.
// To mitigate this if a virtualenv is detected we add its bin directory to the start of the path.
if (process.env.VIRTUAL_ENV) {
  process.env.PATH = process.env.VIRTUAL_ENV.concat(
    path.sep,
    process.platform === 'win32' ? 'Scripts;' : 'bin:',
    process.env.PATH ?? '',
  );
}
