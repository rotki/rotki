import type { build, InlineConfig, LogLevel } from 'vite';
import path from 'node:path';
import process from 'node:process';

export type BuildOutput = Awaited<ReturnType<typeof build>>;

export const mode: 'production' | 'development' = (process.env.NODE_ENV = process.env.NODE_ENV !== 'development' ? 'production' : 'development');

export const LOG_LEVEL: LogLevel = 'info';

export const sharedConfig: InlineConfig = {
  mode,
  logLevel: LOG_LEVEL,
};

// On some systems electron puts /usr/bin ahead of the virtualenv and picks the system python.
if (process.env.VIRTUAL_ENV) {
  process.env.PATH = process.env.VIRTUAL_ENV.concat(
    path.sep,
    process.platform === 'win32' ? 'Scripts;' : 'bin:',
    process.env.PATH ?? '',
  );
}
