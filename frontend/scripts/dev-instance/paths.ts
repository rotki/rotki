import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

const APP_NAME = 'rotki';
const PROD_DATA_SUBDIR = 'data';
const DEV_PARENT_NAME = 'rotki-dev';

export function sanitizeName(raw: string): string {
  const trimmed = raw.trim().toLowerCase();
  const sanitized = trimmed.replace(/[^\d._a-z-]+/g, '-').replace(/^-+|-+$/g, '');
  if (!sanitized) {
    throw new Error(`Instance name "${raw}" sanitizes to an empty string`);
  }
  if (sanitized.length > 64) {
    return sanitized.slice(0, 64);
  }
  return sanitized;
}

export function baseDataDir(): string {
  const platform = os.platform();
  const home = os.homedir();
  if (platform === 'win32') {
    return process.env.LOCALAPPDATA ?? path.join(home, 'AppData', 'Local');
  }
  if (platform === 'darwin') {
    return path.join(home, 'Library', 'Application Support');
  }
  return process.env.XDG_DATA_HOME ?? path.join(home, '.local', 'share');
}

/**
 * Resolves the prod rotki user-data dir (the `--data-dir` rotkehlchen expects).
 *
 * Layout on a typical install is `<XDG_DATA_HOME>/rotki/data/` (with `users/`,
 * `globaldb.sqlite`, etc. inside). The outer `<XDG_DATA_HOME>/rotki/` dir also
 * holds electron cache/logs/develop_data which we do NOT want to seed from.
 *
 * `ROTKI_SEED_SOURCE` overrides this — point it at any directory you want to
 * use as the seed (e.g. `<XDG_DATA_HOME>/rotki/develop_data` to clone the
 * existing dev mirror instead of prod data).
 */
export function resolveSeedSource(): string | null {
  const override = process.env.ROTKI_SEED_SOURCE;
  if (override) {
    return fs.existsSync(override) ? override : null;
  }
  const candidate = path.join(baseDataDir(), APP_NAME, PROD_DATA_SUBDIR);
  return fs.existsSync(candidate) ? candidate : null;
}

export function resolveInstanceParent(): string {
  const override = process.env.ROTKI_DEV_INSTANCES_DIR;
  if (override) {
    return override;
  }
  return path.join(baseDataDir(), DEV_PARENT_NAME);
}

export function resolveInstanceDir(name: string): string {
  return path.join(resolveInstanceParent(), sanitizeName(name));
}

export function ensureInstanceParent(): string {
  const parent = resolveInstanceParent();
  fs.mkdirSync(parent, { recursive: true });
  return parent;
}
